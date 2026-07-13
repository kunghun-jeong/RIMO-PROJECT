"""
yolo_greet.py - 사람을 찾아서 다가가 인사하는 동작

상태 머신:
  SEARCHING  → rotate left 하며 person 탐색
  ALIGNING   → person이 화면 중앙에 오도록 회전 조정
  APPROACHING → person을 향해 천천히 직진
  GREETING   → 앞뒤 인사 동작 시퀀스 실행
  DONE       → 완료 정지
"""

import time
import threading

from .yolo_base import get_model, read_frame, create_ws, ws_publish, STOP_CMD
from .connection import ACTION_MAP

# ── 상태 정의 ─────────────────────────────────────────────────────────────────
STATE_SEARCHING  = "searching"
STATE_ALIGNING   = "aligning"
STATE_APPROACHING = "approaching"
STATE_GREETING   = "greeting"
STATE_DONE       = "done"

# ── 튜닝 파라미터 ─────────────────────────────────────────────────────────────
CONF_THRESHOLD   = 0.5    # 최소 감지 신뢰도
ALIGN_MARGIN     = 0.12   # 중앙 판정 범위 (0.5 ± 0.12)
APPROACH_SIZE    = 0.15   # 이 크기 이상이면 충분히 가까운 것
DETECT_HZ        = 8      # 감지 루프 주파수
SEARCH_TIMEOUT   = 15.0   # 탐색 최대 시간 (초) 초과 시 DONE

# ── 모듈 상태 ─────────────────────────────────────────────────────────────────
_ws          = None
_thread_stop = threading.Event()
_current_cmd = None
_cmd_lock    = threading.Lock()

_state = {
    "running": False,
    "phase":   STATE_DONE,
    "detection": {
        "class":      None,
        "confidence": 0.0,
        "position":   None,
        "size_ratio": 0.0,
    },
}


# ── 인사 시퀀스 (블로킹) ──────────────────────────────────────────────────────

def _execute_greeting():
    """강아지 인사 동작. publish_loop이 이 명령들을 10Hz로 전송."""
    global _current_cmd
    steps = [
        # 반갑다고 좌우로 흔들기
        ("sharp left",       0.25),
        ("sharp right",      0.25),
        ("sharp left",       0.25),
        ("sharp right",      0.25),
        ("stop",             0.2),
        # 앞뒤 인사 (절하기)
        ("go straight slow", 0.5),
        ("stop",             0.3),
        ("move back slow",   0.5),
        ("stop",             0.3),
        # 신나서 원 그리기
        ("curve left",       2.2),
        ("stop",             0.3),
    ]
    for cmd_name, duration in steps:
        with _cmd_lock:
            _current_cmd = ACTION_MAP[cmd_name]
        time.sleep(duration)


# ── 메인 감지·제어 루프 ───────────────────────────────────────────────────────

def _detection_loop():
    global _current_cmd
    model       = get_model()
    search_start = time.time()

    while not _thread_stop.is_set():
        if not _state["running"]:
            time.sleep(0.1)
            continue

        phase = _state["phase"]

        # ── DONE ──────────────────────────────────────────────────────────
        if phase == STATE_DONE:
            with _cmd_lock:
                _current_cmd = STOP_CMD
            break

        # ── SEARCHING ─────────────────────────────────────────────────────
        if phase == STATE_SEARCHING:
            with _cmd_lock:
                _current_cmd = ACTION_MAP["rotate left"]

            if time.time() - search_start > SEARCH_TIMEOUT:
                print("[GREET] 탐색 시간 초과 → 종료")
                _state["phase"] = STATE_DONE
                continue

            ret, frame = read_frame()
            if not ret:
                time.sleep(1.0 / DETECT_HZ)
                continue

            results = model(frame, verbose=False)
            matched = [b for b in (results[0].boxes or [])
                       if model.names[int(b.cls[0])] == "person"
                       and float(b.conf[0]) >= CONF_THRESHOLD]

            if matched:
                print("[GREET] person 발견 → ALIGNING")
                _state["phase"] = STATE_ALIGNING

        # ── ALIGNING ──────────────────────────────────────────────────────
        elif phase == STATE_ALIGNING:
            ret, frame = read_frame()
            if not ret:
                time.sleep(1.0 / DETECT_HZ)
                continue

            results = model(frame, verbose=False)
            matched = [b for b in (results[0].boxes or [])
                       if model.names[int(b.cls[0])] == "person"
                       and float(b.conf[0]) >= CONF_THRESHOLD]

            if not matched:
                print("[GREET] person 놓침 → SEARCHING")
                search_start = time.time()
                _state["phase"] = STATE_SEARCHING
                time.sleep(1.0 / DETECT_HZ)
                continue

            best  = max(matched, key=lambda b: float(b.conf[0]))
            x1,y1,x2,y2 = best.xyxy[0]
            cx    = float((x1 + x2) / 2)
            ratio = cx / frame.shape[1]
            conf  = float(best.conf[0])

            _state["detection"].update({
                "class": "person", "confidence": round(conf, 2),
                "position": "left" if ratio < 0.38 else ("right" if ratio > 0.62 else "center"),
                "size_ratio": round((float(x2-x1)*float(y2-y1))/(frame.shape[1]*frame.shape[0]), 3),
            })

            if ratio < (0.5 - ALIGN_MARGIN):
                print(f"[GREET] 왼쪽 정렬 중 ratio={ratio:.2f}")
                with _cmd_lock:
                    _current_cmd = ACTION_MAP["rotate left"]
            elif ratio > (0.5 + ALIGN_MARGIN):
                print(f"[GREET] 오른쪽 정렬 중 ratio={ratio:.2f}")
                with _cmd_lock:
                    _current_cmd = ACTION_MAP["rotate right"]
            else:
                print(f"[GREET] 정렬 완료 ratio={ratio:.2f} → APPROACHING")
                with _cmd_lock:
                    _current_cmd = STOP_CMD
                time.sleep(0.3)
                _state["phase"] = STATE_APPROACHING

        # ── APPROACHING ───────────────────────────────────────────────────
        elif phase == STATE_APPROACHING:
            ret, frame = read_frame()
            if not ret:
                time.sleep(1.0 / DETECT_HZ)
                continue

            results = model(frame, verbose=False)
            matched = [b for b in (results[0].boxes or [])
                       if model.names[int(b.cls[0])] == "person"
                       and float(b.conf[0]) >= CONF_THRESHOLD]

            if not matched:
                print("[GREET] person 놓침 → SEARCHING")
                search_start = time.time()
                _state["phase"] = STATE_SEARCHING
                time.sleep(1.0 / DETECT_HZ)
                continue

            best       = max(matched, key=lambda b: float(b.conf[0]))
            x1,y1,x2,y2 = best.xyxy[0]
            cx         = float((x1 + x2) / 2)
            ratio      = cx / frame.shape[1]
            size_ratio = (float(x2-x1)*float(y2-y1)) / (frame.shape[1]*frame.shape[0])
            conf       = float(best.conf[0])

            _state["detection"].update({
                "class": "person", "confidence": round(conf, 2),
                "position": "left" if ratio < 0.38 else ("right" if ratio > 0.62 else "center"),
                "size_ratio": round(size_ratio, 3),
            })

            print(f"[GREET] 접근 중 size={size_ratio:.3f} ratio={ratio:.2f}")

            if size_ratio >= APPROACH_SIZE:
                print("[GREET] 충분히 가까움 → GREETING")
                with _cmd_lock:
                    _current_cmd = STOP_CMD
                time.sleep(0.4)
                _state["phase"] = STATE_GREETING
            elif ratio < 0.35:
                with _cmd_lock:
                    _current_cmd = ACTION_MAP["turn left"]
            elif ratio > 0.65:
                with _cmd_lock:
                    _current_cmd = ACTION_MAP["turn right"]
            elif size_ratio < APPROACH_SIZE * 0.5:
                # 아직 많이 멀면 빠르게 접근
                with _cmd_lock:
                    _current_cmd = ACTION_MAP["go straight fast"]
            else:
                # 가까워질수록 속도 줄이기
                with _cmd_lock:
                    _current_cmd = ACTION_MAP["go straight"]

        # ── GREETING ──────────────────────────────────────────────────────
        elif phase == STATE_GREETING:
            print("[GREET] 인사 동작 시작!")
            _execute_greeting()
            print("[GREET] 인사 완료 → DONE")
            _state["phase"] = STATE_DONE
            continue

        time.sleep(1.0 / DETECT_HZ)

    _state["running"] = False
    with _cmd_lock:
        _current_cmd = STOP_CMD
    print("[GREET] 루프 종료")


def _publish_loop():
    global _ws
    while not _thread_stop.is_set():
        if _state["running"] or _state["phase"] == STATE_GREETING:
            with _cmd_lock:
                cmd = _current_cmd
            if cmd is not None and _ws is not None:
                try:
                    ws_publish(_ws, cmd)
                except Exception as e:
                    print(f"[GREET] publish 실패: {e}")
                    _ws = None
        time.sleep(0.1)


# ── 공개 API ─────────────────────────────────────────────────────────────────

def start():
    global _ws, _current_cmd
    _state["running"] = True
    _state["phase"]   = STATE_SEARCHING
    _state["detection"] = {"class": None, "confidence": 0.0, "position": None, "size_ratio": 0.0}

    get_model()

    try:
        _ws = create_ws()
    except Exception as e:
        print(f"[GREET] rosbridge 연결 실패: {e}")
        _ws = None

    _thread_stop.clear()
    _current_cmd = STOP_CMD

    threading.Thread(target=_detection_loop, daemon=True).start()
    threading.Thread(target=_publish_loop,   daemon=True).start()

    print("[GREET] 인사 모드 시작 - 사람을 탐색합니다")
    return True


def stop():
    global _ws, _current_cmd
    _state["running"] = False
    _state["phase"]   = STATE_DONE
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
    print("[GREET] 강제 정지")
    return True


def get_status():
    return {
        "running":   _state["running"],
        "phase":     _state["phase"],
        "detection": _state["detection"],
    }
