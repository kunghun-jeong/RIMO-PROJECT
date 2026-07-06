import yaml
import os

# LIMO 연결 정보 (연결 시 IP 변경)
LIMO_HOST = "192.168.50.165"
LIMO_PORT = 9090  # rosbridge 기본 포트

# cmd_vel 매핑 테이블
ACTION_MAP = {
    "go straight": {"linear": {"x": 0.5, "y": 0.0, "z": 0.0}, "angular": {"x": 0.0, "y": 0.0, "z": 0.0}},
    "stop":        {"linear": {"x": 0.0, "y": 0.0, "z": 0.0}, "angular": {"x": 0.0, "y": 0.0, "z": 0.0}},
    "turn left":   {"linear": {"x": 0.3, "y": 0.0, "z": 0.0}, "angular": {"x": 0.0, "y": 0.0, "z": 0.5}},
    "turn right":  {"linear": {"x": 0.3, "y": 0.0, "z": 0.0}, "angular": {"x": 0.0, "y": 0.0, "z": -0.5}},
    "move back":   {"linear": {"x": -0.5, "y": 0.0, "z": 0.0}, "angular": {"x": 0.0, "y": 0.0, "z": 0.0}},
}


def read_policy_yaml(yaml_path: str) -> dict:
    with open(yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def extract_action(policy: dict) -> str:
    try:
        return policy["intentActions"][0]["actionType"].lower()
    except (KeyError, IndexError, TypeError):
        return "go straight"


def action_to_cmd_vel(action: str) -> dict:
    # 매핑 테이블에 없으면 stop
    return ACTION_MAP.get(action, ACTION_MAP["go straight"])


def send_to_limo(cmd_vel: dict, duration: float = 2.0) -> bool:
    try:
        import websocket
        import json
        import time

        ws = websocket.create_connection(f"ws://{LIMO_HOST}:{LIMO_PORT}")
        time.sleep(0.3)  # 연결 안정화 대기

        # topic advertise
        ws.send(json.dumps({
            "op": "advertise",
            "topic": "/cmd_vel",
            "type": "geometry_msgs/msg/Twist"
        }))
        time.sleep(0.2)

        def publish(msg):
            ws.send(json.dumps({
                "op": "publish",
                "topic": "/cmd_vel",
                "msg": msg
            }))

        # duration 동안 지속 퍼블리시 (0.1초 간격)
        end_time = time.time() + duration
        while time.time() < end_time:
            publish(cmd_vel)
            time.sleep(0.1)

        # 정지 명령 전송
        stop = {"linear": {"x": 0.0, "y": 0.0, "z": 0.0}, "angular": {"x": 0.0, "y": 0.0, "z": 0.0}}
        publish(stop)
        time.sleep(0.1)

        ws.close()
        print(f"[LIMO] cmd_vel 전송 완료: {cmd_vel} / duration: {duration}s")
        return True

    except Exception as e:
        print(f"[LIMO] 전송 실패: {e}")
        return False


def run(yaml_path: str) -> dict:
    policy = read_policy_yaml(yaml_path)
    action = extract_action(policy)
    cmd_vel = action_to_cmd_vel(action)

    print(f"[LIMO] action: {action} → cmd_vel: {cmd_vel}")

    success = send_to_limo(cmd_vel)

    return {
        "action": action,
        "cmd_vel": cmd_vel,
        "success": success,
    }
