"""
yolo_trace.py - 특정 물체를 실시간으로 추적하는 동작

구조:
  Thread 1 (_detection_loop): 카메라 프레임 → YOLO 추론 → 명령 결정 → _current_cmd 업데이트
  Thread 2 (_publish_loop)  : _current_cmd를 10Hz로 LIMO에 전송

이동 속도/방향은 ACTION_MAP 테이블 기반 (팀 합의).
YOLO는 어떤 명령을 선택할지만 결정.
"""

import time
import threading

from .yolo_base import get_model, read_frame, create_ws, ws_publish, STOP_CMD
from .connection import ACTION_MAP

# ── 추적 판단 임계값 ─────────────────────────────────────────────────────────
CONF_THRESHOLD  = 0.5    # 이 신뢰도 이하면 감지 무시
SIZE_TOO_CLOSE  = 0.30   # 박스가 화면의 30% 이상 → 너무 가까움 → 후진
SIZE_TOO_FAR    = 0.03   # 박스가 화면의 3% 이하  → 너무 멈 → 직진
LOST_TIMEOUT    = 2.0    # 물체가 안 보인 뒤 정지까지 대기 시간 (초)
DETECT_HZ       = 8      # 감지 루프 주파수

# ── 모듈 상태 ─────────────────────────────────────────────────────────────────
_ws          = None
_thread_stop = threading.Event()
_current_cmd = None
_cmd_lock    = threading.Lock()

_state = {
    "running":      False,
    "target_class": "person",
    "detection": {
        "class":      None,
        "confidence": 0.0,
        "position":   None,    # "left" | "center" | "right"
        "size_ratio": 0.0,
        "command":    "stop",
        "lost":       False,
    },
}


# ── 추적 명령 결정 (테이블 키 반환) ──────────────────────────────────────────

def _get_track_command(cx, box_w, box_h, frame_w, frame_h, conf):
    """물체 위치·크기를 보고 ACTION_MAP 키 중 하나를 반환."""
    if conf < CONF_THRESHOLD:
        return "stop"

    size_ratio = (box_w * box_h) / (frame_w * frame_h)
    ratio      = cx / frame_w

    # 너무 가까우면 후진
    if size_ratio > SIZE_TOO_CLOSE:
        return "move back"

    # 물체가 왼쪽 → 왼쪽으로 회전해서 따라가기
    if ratio < 0.35:
        return "turn left"

    # 물체가 오른쪽 → 오른쪽으로 회전해서 따라가기
    if ratio > 0.65:
        return "turn right"

    # 물체가 중앙에 있고 너무 멀면 직진
    if size_ratio < SIZE_TOO_FAR:
        return "go straight"

    # 중앙에 있고 적정 거리면 정지 (유지)
    return "stop"


# ── 스레드 함수들 ─────────────────────────────────────────────────────────────

def _detection_loop():
    """카메라 읽기 + YOLO 추론을 반복하며 _current_cmd를 업데이트."""
    global _current_cmd
    model     = get_model()
    last_seen = time.time()

    while not _thread_stop.is_set():
        if not _state["running"]:
            time.sleep(0.1)
            continue

        ret, frame = read_frame()
        if not ret:
            time.sleep(0.1)
            continue

        target  = _state["target_class"]
        results = model(frame, verbose=False)
        boxes   = results[0].boxes
        matched = [b for b in (boxes or [])
                   if model.names[int(b.cls[0])] == target
                   and float(b.conf[0]) >= CONF_THRESHOLD]

        if matched:
            best         = max(matched, key=lambda b: float(b.conf[0]))
            x1, y1, x2, y2 = best.xyxy[0]
            cx           = float((x1 + x2) / 2)
            box_w        = float(x2 - x1)
            box_h        = float(y2 - y1)
            conf         = float(best.conf[0])
            size_ratio   = (box_w * box_h) / (frame.shape[1] * frame.shape[0])
            ratio        = cx / frame.shape[1]
            pos          = "left" if ratio < 0.35 else ("right" if ratio > 0.65 else "center")
            command      = _get_track_command(cx, box_w, box_h, frame.shape[1], frame.shape[0], conf)

            _state["detection"].update({
                "class":      target,
                "confidence": round(conf, 2),
                "position":   pos,
                "size_ratio": round(size_ratio, 3),
                "command":    command,
                "lost":       False,
            })
            print(f"[TRACE] {target} ({conf:.2f}) {pos} size={size_ratio:.3f} → {command}")

            with _cmd_lock:
                _current_cmd = ACTION_MAP[command]

            last_seen = time.time()

        else:
            if time.time() - last_seen > LOST_TIMEOUT:
                _state["detection"]["lost"] = True
                with _cmd_lock:
                    _current_cmd = STOP_CMD

        time.sleep(1.0 / DETECT_HZ)


def _publish_loop():
    """10Hz로 현재 명령을 LIMO에 전송."""
    global _ws
    while not _thread_stop.is_set():
        if _state["running"]:
            with _cmd_lock:
                cmd = _current_cmd
            if cmd is not None and _ws is not None:
                try:
                    ws_publish(_ws, cmd)
                except Exception as e:
                    print(f"[TRACE] publish 실패: {e}")
                    _ws = None
        time.sleep(0.1)


# ── 공개 API ─────────────────────────────────────────────────────────────────

def start(target_class="person"):
    global _ws, _current_cmd
    _state["running"]           = True
    _state["target_class"]      = target_class
    _state["detection"]["lost"] = False

    get_model()

    try:
        _ws = create_ws()
    except Exception as e:
        print(f"[TRACE] rosbridge 연결 실패: {e}")
        _ws = None

    _thread_stop.clear()
    _current_cmd = STOP_CMD

    threading.Thread(target=_detection_loop, daemon=True).start()
    threading.Thread(target=_publish_loop,   daemon=True).start()

    print(f"[TRACE] 시작 - 추적 대상: {target_class}")
    return True


def stop():
    global _ws, _current_cmd
    _state["running"] = False
    _thread_stop.set()
    time.sleep(0.2)

    if _ws is not None:
        try:
            ws_publish(_ws, STOP_CMD)
            _ws.close()
        except Exception:
            pass
        _ws = None

    _current_cmd = None
    print("[TRACE] 정지")
    return True


def get_status():
    return {
        "running":      _state["running"],
        "target_class": _state["target_class"],
        "detection":    _state["detection"],
    }
