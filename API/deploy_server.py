"""
리모카 전용 배포 서버 - /policy/deploy 만 담당
RestAPI.py의 무거운 의존성(pyangbind, generatorv2 등) 없이 독립 실행 가능
"""
import os
import json
import subprocess
from flask import Flask, request, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

ROS2_CMD_DIR = os.path.join(os.path.dirname(__file__), "ros2_commands")


def execute_ros2_file(sh_file_path: str):
    if not os.path.exists(sh_file_path):
        msg = f"ROS2 파일을 찾을 수 없습니다: {sh_file_path}"
        print(f"[ROS2] {msg}")
        return False, msg

    print(f"[ROS2] 파일 실행: {sh_file_path}")
    result = subprocess.run(
        ["bash", sh_file_path],
        capture_output=True, text=True, timeout=30
    )

    if result.returncode == 0:
        print(f"[ROS2] 전송 성공")
        return True, result.stdout
    else:
        print(f"[ROS2] 전송 실패: {result.stderr}")
        return False, result.stderr


@app.route('/policy/deploy', methods=['POST'])
def deploy_policy():
    data = request.json
    if not data or 'command' not in data:
        return Response(
            json.dumps({"error": "command 필드가 필요합니다 (예: \"forward\")"}),
            status=400, mimetype='application/json'
        )

    command = data['command']
    sh_path = os.path.join(ROS2_CMD_DIR, f"{command}.sh")

    # 다른 팀이 .sh 내용을 직접 전달한 경우 저장
    sh_content = data.get('sh_content', '')
    if sh_content:
        os.makedirs(ROS2_CMD_DIR, exist_ok=True)
        with open(sh_path, 'w', encoding='utf-8') as f:
            f.write(sh_content)
        print(f"[DEPLOY] ROS2 파일 저장: {sh_path}")

    success, message = execute_ros2_file(sh_path)

    status_code = 200 if success else 500
    return Response(
        json.dumps({"status": "success" if success else "failed",
                    "command": command,
                    "message": message}),
        status=status_code, mimetype='application/json'
    )


@app.route('/health', methods=['GET'])
def health():
    return Response(json.dumps({"status": "ok"}), status=200, mimetype='application/json')


if __name__ == '__main__':
    print("리모카 배포 서버 시작: http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000)
