import json
import time
import threading
import requests
import websocket
from .connection import ACTION_MAP, LIMO_HOST, LIMO_PORT

try:
    import cv2
    import numpy as np
    from ultralytics import YOLO
    _YOLO_AVAILABLE = True
except ImportError:
    _YOLO_AVAILABLE = False
    print("[YOLO] cv2/ultralytics not installed - YOLO disabled")

SNAPSHOT_URL = f"http://{LIMO_HOST}:8080/snapshot"

_model       = None
_ws          = None
_thread      = None
_thread_stop = threading.Event()
_current_cmd = None
_cmd_lock    = threading.Lock()

_state = {
    "running":   False,
    "detection": {"class": None, "confidence": 0.0, "position": None, "command": "stop"},
}

STOP_CMD = {"linear": {"x": 0.0, "y": 0.0, "z": 0.0}, "angular": {"x": 0.0, "y": 0.0, "z": 0.0}}


def _get_model():
    global _model
    if _model is None:
        _model = YOLO("yolo11n.pt")
        print("[YOLO] 모델 로드 완료")
    return _model


def _read_frame():
    try:
        r = requests.get(SNAPSHOT_URL, timeout=3)
        if r.status_code != 200:
            return False, None
        frame = cv2.imdecode(np.frombuffer(r.content, dtype=np.uint8), cv2.IMREAD_COLOR)
        return (True, frame) if frame is not None else (False, None)
    except Exception as e:
        print(f"[YOLO] 카메라 오류: {e}")
    return False, None


def _ensure_ws():
    global _ws
    if _ws is not None:
        return True
    try:
        _ws = websocket.create_connection(f"ws://{LIMO_HOST}:{LIMO_PORT}", timeout=5)
        time.sleep(0.3)
        _ws.send(json.dumps({
            "op": "advertise",
            "topic": "/cmd_vel",
            "type": "geometry_msgs/msg/Twist"
        }))
        time.sleep(0.2)
        print("[YOLO] rosbridge 연결됨")
        return True
    except Exception as e:
        print(f"[YOLO] rosbridge 연결 실패: {e}")
        _ws = None
        return False


def _ws_publish(cmd_vel):
    global _ws
    try:
        if not _ensure_ws():
            return False
        _ws.send(json.dumps({
            "op": "publish",
            "topic": "/cmd_vel",
            "msg": cmd_vel
        }))
        return True
    except Exception as e:
        print(f"[YOLO] publish 실패: {e}")
        _ws = None
        return False


def _publish_loop():
    """10Hz로 현재 명령을 지속 전송하는 백그라운드 스레드."""
    while not _thread_stop.is_set():
        if _state["running"]:
            with _cmd_lock:
                cmd = _current_cmd
            if cmd is not None:
                _ws_publish(cmd)
        time.sleep(0.1)


def _get_command(cx, frame_width, conf):
    if conf < 0.5:
        return "go straight"
    ratio = cx / frame_width
    if ratio < 0.35:
        return "turn right"
    elif ratio > 0.65:
        return "turn left"
    else:
        return "turn left"


def start():
    global _thread, _current_cmd
    _state["running"] = True
    _get_model()
    _ensure_ws()

    _thread_stop.clear()
    _current_cmd = ACTION_MAP["go straight"]

    _thread = threading.Thread(target=_publish_loop, daemon=True)
    _thread.start()

    print(f"[YOLO] 시작. 카메라: {SNAPSHOT_URL}")
    return True


def stop():
    global _ws, _thread, _current_cmd
    _state["running"] = False
    _thread_stop.set()

    if _thread:
        _thread.join(timeout=1.0)
        _thread = None

    _current_cmd = None
    _ws_publish(STOP_CMD)

    if _ws:
        try:
            _ws.close()
        except Exception:
            pass
        _ws = None
    return True


def tick():
    global _current_cmd
    if not _state["running"]:
        return _state

    model = _get_model()

    ret, frame = _read_frame()
    if not ret or frame is None:
        print("[YOLO] 카메라 읽기 실패")
        return _state

    results    = model(frame, verbose=False)
    detections = results[0].boxes

    if detections is not None and len(detections) > 0:
        best    = max(detections, key=lambda b: float(b.conf[0]))
        cx      = float((best.xyxy[0][0] + best.xyxy[0][2]) / 2)
        conf    = float(best.conf[0])
        cls     = model.names[int(best.cls[0])]
        ratio   = cx / frame.shape[1]
        pos     = "left" if ratio < 0.35 else ("right" if ratio > 0.65 else "center")
        command = _get_command(cx, frame.shape[1], conf)

        _state["detection"] = {
            "class": cls, "confidence": round(conf, 2),
            "position": pos, "command": command,
        }
        print(f"[YOLO] {cls} ({conf:.2f}) {pos} → {command}")
    else:
        command = "go straight"
        _state["detection"] = {
            "class": None, "confidence": 0.0,
            "position": None, "command": "go straight",
        }

    with _cmd_lock:
        _current_cmd = ACTION_MAP[command]

    return _state


def get_status():
    return {
        "running":   _state["running"],
        "detection": _state["detection"],
    }
