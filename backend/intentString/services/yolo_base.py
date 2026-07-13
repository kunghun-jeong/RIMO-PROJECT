import json
import time
import requests

try:
    import cv2
    import numpy as np
    from ultralytics import YOLO
    _YOLO_AVAILABLE = True
except ImportError:
    _YOLO_AVAILABLE = False
    print("[YOLO] cv2/ultralytics not installed - YOLO disabled")

from .connection import LIMO_HOST, LIMO_PORT

SNAPSHOT_URL = f"http://{LIMO_HOST}:8080/snapshot"
STOP_CMD = {"linear": {"x": 0.0, "y": 0.0, "z": 0.0},
            "angular": {"x": 0.0, "y": 0.0, "z": 0.0}}

_model = None


def get_model(model_name="yolo11n.pt"):
    global _model
    if _model is None:
        _model = YOLO(model_name)
        print(f"[YOLO] 모델 로드 완료: {model_name}")
    return _model


def read_frame():
    """카메라에서 프레임 한 장을 읽어 반환. 실패 시 (False, None)."""
    try:
        r = requests.get(SNAPSHOT_URL, timeout=3)
        if r.status_code != 200:
            return False, None
        frame = cv2.imdecode(np.frombuffer(r.content, dtype=np.uint8), cv2.IMREAD_COLOR)
        return (True, frame) if frame is not None else (False, None)
    except Exception as e:
        print(f"[YOLO] 카메라 오류: {e}")
    return False, None


def create_ws(host=LIMO_HOST, port=LIMO_PORT):
    """rosbridge WebSocket 연결 생성 및 /cmd_vel advertise."""
    import websocket
    ws = websocket.create_connection(f"ws://{host}:{port}", timeout=5)
    time.sleep(0.3)
    ws.send(json.dumps({
        "op": "advertise",
        "topic": "/cmd_vel",
        "type": "geometry_msgs/msg/Twist"
    }))
    time.sleep(0.2)
    print("[YOLO] rosbridge 연결됨")
    return ws


def ws_publish(ws, cmd_vel):
    """WebSocket으로 cmd_vel 메시지 전송."""
    ws.send(json.dumps({
        "op": "publish",
        "topic": "/cmd_vel",
        "msg": cmd_vel
    }))


def clamp(value, min_val, max_val):
    return max(min_val, min(max_val, value))
