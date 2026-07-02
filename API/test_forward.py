"""
리모카(LIMO) 앞으로 가기 테스트
- ROS2가 설치된 환경에서 실행
- LIMO와 같은 네트워크(192.168.50.x)에 연결된 상태여야 함
"""
import socketAPI

print("=== LIMO 앞으로 가기 테스트 ===")
success, msg = socketAPI.send_policy_to_rimoca("go straight")

if success:
    print("[OK] 명령 전송 성공")
    print(msg)
else:
    print("[FAIL] 명령 전송 실패")
    print(msg)
