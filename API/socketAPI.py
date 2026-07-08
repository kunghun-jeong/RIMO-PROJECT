import os
import sys
import socket
import threading
import subprocess

ROS2_CMD_DIR = os.path.join(os.path.dirname(__file__), "ros2_commands")

def execute_ros2_file(sh_file_path: str) -> tuple:
    """
    다른 팀이 생성한 ROS2 쉘 파일을 실행해서 LIMO에 명령 전송.
    sh_file_path: ros2_commands/ 아래의 .sh 파일 경로 (절대경로)
    """
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


def get_ros2_file_path(command_name: str) -> str:
    """command_name → ros2_commands/{command_name}.sh 절대경로 반환"""
    return os.path.join(ROS2_CMD_DIR, f"{command_name}.sh")


def openRegistrationInterface(IP, PORT, converter):
    server_socket1 = socket.socket()
    server_socket1.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket1.bind((IP, PORT))
    server_socket1.listen(0)
    while True:
        client_socket1, addr = server_socket1.accept()
        print('DMS is connected to Security Controller')
        data = client_socket1.recv(1024)
        converter.registerNSF(data)

def request_nsf(IP, PORT, nsf_name):
    ADDR = (IP, PORT)
    client_socket2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket2.connect(ADDR)
        client_socket2.send(nsf_name)
    except Exception as e:
        print("%s:%s" % ADDR)
        sys.exit()

def receive_nsf_ip(IP, PORT):
    server_socket = socket.socket()
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((IP, PORT))
    server_socket.listen(5)
    while True:
        client_socket, addr = server_socket.accept()
        data = client_socket.recv(1024)
        data = data.split(",")
        os.system("/home/ubuntu/confd-6.6/bin/netconf-console --host "+data[1]+" /home/ubuntu/LowLevelPolicy/"+data[0]+".xml")
