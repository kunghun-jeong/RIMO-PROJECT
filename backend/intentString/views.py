import paramiko
from rest_framework import viewsets, status
from rest_framework.response import Response
from .serializers import NaturalIntentSerializer
from .models import NaturalIntent

LIMO_HOST = "192.168.50.165"
LIMO_USER = "agilex"
LIMO_PASS = "agx"
ROS2_CMD = (
    "source /opt/ros/humble/setup.bash 2>/dev/null && "
    "source /home/agilex/agilex_ws/install/setup.bash 2>/dev/null && "
    "ros2 topic pub --times 20 -r 10 --wait-matching-subscriptions 0 "
    "/cmd_vel geometry_msgs/msg/Twist "
    "'{linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}'"
)


def limo_forward():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(LIMO_HOST, username=LIMO_USER, password=LIMO_PASS, timeout=10)
        _, stdout, stderr = ssh.exec_command(f'bash -c "{ROS2_CMD}"', timeout=35)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace")
        ssh.close()
        print(f"[LIMO] exit={exit_code} out={out[:200]} err={err[:200]}")
        return {"status": "success" if exit_code == 0 else "failed",
                "exit": exit_code, "out": out, "err": err}
    except Exception as e:
        print(f"[LIMO] SSH 오류: {e}")
        return {"status": "failed", "error": str(e)}


class NaturalIntentViewSet(viewsets.ModelViewSet):
    queryset = NaturalIntent.objects.all()
    serializer_class = NaturalIntentSerializer

    def create(self, request, *args, **kwargs):
        print(f"[RECV] intent: {request.data.get('intent', '')}")
        result = limo_forward()
        return Response(result, status=status.HTTP_200_OK)
