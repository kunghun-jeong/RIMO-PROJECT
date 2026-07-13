"""
limo_pure_pursuit.py
────────────────────
LIMO에 직접 올려서 실행하는 독립 Pure Pursuit 노드.

의존 패키지 (ROS2 humble 기준):
    sudo apt install ros-humble-tf2-ros ros-humble-geometry-msgs

실행:
    python3 limo_pure_pursuit.py

구독 토픽:
    /astar_waypoints  (std_msgs/String) — JSON 경로 "[{x,y}, ...]"
    /navigation_stop  (std_msgs/String) — "stop" / "resume"

발행 토픽:
    /cmd_vel  (geometry_msgs/Twist)
"""

import math
import json
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Twist
import tf2_ros


class LimoPurePursuit(Node):
    def __init__(self):
        super().__init__("limo_pure_pursuit")

        # ── Pure Pursuit 파라미터 ──────────────────────────
        self.lookahead_distance    = 0.8   # 전방 주시 거리 [m]
        self.goal_tolerance        = 0.35  # 최종 목표 도달 판정 거리 [m]

        self.max_linear            = 0.8
        self.min_linear            = 0.1
        self.max_angular           = 1.0
        self.linear_speed          = 0.5   # 기본 직진 속도
        self.angular_k             = 1.5   # 조향 gain

        self.heading_slowdown_angle = 1.2  # 이 각도 이상 틀어지면 감속 [rad]

        self.max_linear_step       = 0.05  # 속도 변화 제한 (부드러운 가감속)
        self.max_angular_step      = 0.1

        # ── 상태 ──────────────────────────────────────────
        self.active_route          = []
        self.active_route_name     = None
        self.is_running            = False
        self.closest_segment_idx   = 0
        self.prev_linear           = 0.0
        self.prev_angular          = 0.0

        # ── ROS 설정 ───────────────────────────────────────
        self.robot_frame = "base_link"
        self.odom_frame  = "odom"

        self.cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)

        self.create_subscription(
            String, "/astar_waypoints",
            self._on_astar_waypoints, 10
        )
        self.create_subscription(
            String, "/navigation_stop",
            self._on_navigation_stop, 10
        )

        self.tf_buffer   = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        # 20 Hz 제어 루프
        self.create_timer(0.05, self._control_loop)

        self.get_logger().info("LimoPurePursuit 시작")
        self.get_logger().info("/astar_waypoints 토픽 대기 중...")

    # ── 토픽 콜백 ────────────────────────────────────────

    def _on_astar_waypoints(self, msg: String):
        try:
            points = json.loads(msg.data)
            route  = [(float(p["x"]), float(p["y"])) for p in points]
        except Exception as e:
            self.get_logger().warn(f"[A*] 경로 파싱 실패: {e}")
            return

        if len(route) < 2:
            self.get_logger().warn("[A*] 포인트가 2개 미만 — 무시")
            return

        self.active_route          = route
        self.active_route_name     = "astar"
        self.closest_segment_idx   = 0
        self.is_running            = True
        self.prev_linear           = 0.0
        self.prev_angular          = 0.0

        self.get_logger().info(
            f"[A*] 경로 수신 완료: {len(route)}포인트 "
            f"| 시작 {route[0]} → 도착 {route[-1]}"
        )

    def _on_navigation_stop(self, msg: String):
        cmd = msg.data.strip()
        if cmd == "stop":
            self.get_logger().warn("[Nav] 정지 명령 수신")
            self._stop_robot()
            self.is_running = False
        elif cmd == "resume":
            if len(self.active_route) >= 2:
                self.is_running   = True
                self.prev_linear  = 0.0
                self.prev_angular = 0.0
                self.get_logger().info("[Nav] 재개")
            else:
                self.get_logger().warn("[Nav] 재개할 경로 없음")

    # ── 제어 루프 (20 Hz) ────────────────────────────────

    def _control_loop(self):
        if not self.is_running or len(self.active_route) < 2:
            return

        pose = self._get_robot_pose()
        if pose is None:
            self._stop_robot()
            return

        rx, ry, ryaw = pose
        robot_pos    = (rx, ry)
        final_goal   = self.active_route[-1]

        # 최종 목표 도달 판정
        if self._dist(robot_pos, final_goal) < self.goal_tolerance:
            self.get_logger().info(
                f"[A*] 목표 도달! 경로 '{self.active_route_name}' 완료"
            )
            self._stop_robot()
            self.is_running = False
            return

        # Lookahead point 계산
        lx, ly = self._get_lookahead_point(robot_pos)

        dx         = lx - rx
        dy         = ly - ry
        target_yaw = math.atan2(dy, dx)
        yaw_err    = self._normalize_angle(target_yaw - ryaw)

        # 헤딩 오차 기반 감속
        heading_factor = max(0.0, 1.0 - abs(yaw_err) / self.heading_slowdown_angle)

        # 목표 근접 감속
        goal_dist   = self._dist(robot_pos, final_goal)
        goal_factor = min(1.0, goal_dist / 1.5)

        target_linear = self.linear_speed * heading_factor * goal_factor
        if 0.0 < target_linear < self.min_linear:
            target_linear = self.min_linear
        target_linear  = self._clamp(target_linear, 0.0, self.max_linear)
        target_angular = self._clamp(self.angular_k * yaw_err, -self.max_angular, self.max_angular)

        cmd = Twist()
        cmd.linear.x  = self._limit_step(target_linear,  self.prev_linear,  self.max_linear_step)
        cmd.angular.z = self._limit_step(target_angular, self.prev_angular, self.max_angular_step)

        self.prev_linear  = cmd.linear.x
        self.prev_angular = cmd.angular.z
        self.cmd_pub.publish(cmd)

    # ── Pure Pursuit 유틸 ────────────────────────────────

    def _get_lookahead_point(self, robot_pos):
        seg_idx, proj, _ = self._find_closest_segment(robot_pos)
        remaining        = self.lookahead_distance
        current_pt       = proj
        current_seg      = seg_idx

        while current_seg < len(self.active_route) - 1:
            next_pt  = self.active_route[current_seg + 1]
            seg_len  = self._dist(current_pt, next_pt)

            if seg_len >= remaining:
                ratio = remaining / max(seg_len, 1e-6)
                lx    = current_pt[0] + ratio * (next_pt[0] - current_pt[0])
                ly    = current_pt[1] + ratio * (next_pt[1] - current_pt[1])
                return lx, ly

            remaining  -= seg_len
            current_seg += 1
            current_pt  = self.active_route[current_seg]

        return self.active_route[-1]

    def _find_closest_segment(self, robot_pos):
        best_dist = float("inf")
        best_idx  = self.closest_segment_idx
        best_proj = self.active_route[0]
        best_t    = 0.0

        start = max(0, self.closest_segment_idx - 1)
        for i in range(start, len(self.active_route) - 1):
            a    = self.active_route[i]
            b    = self.active_route[i + 1]
            proj, t = self._project_to_segment(robot_pos, a, b)
            d    = self._dist(robot_pos, proj)
            if d < best_dist:
                best_dist = d
                best_idx  = i
                best_proj = proj
                best_t    = t

        self.closest_segment_idx = best_idx
        return best_idx, best_proj, best_t

    def _project_to_segment(self, p, a, b):
        abx = b[0] - a[0]; aby = b[1] - a[1]
        apx = p[0] - a[0]; apy = p[1] - a[1]
        denom = abx * abx + aby * aby
        if denom < 1e-6:
            return a, 0.0
        t    = self._clamp((apx * abx + apy * aby) / denom, 0.0, 1.0)
        proj = (a[0] + t * abx, a[1] + t * aby)
        return proj, t

    # ── TF (로봇 위치) ────────────────────────────────────

    def _get_robot_pose(self):
        try:
            tf = self.tf_buffer.lookup_transform(
                self.odom_frame, self.robot_frame, rclpy.time.Time()
            )
            x = tf.transform.translation.x
            y = tf.transform.translation.y
            q = tf.transform.rotation
            yaw = math.atan2(
                2.0 * (q.w * q.z + q.x * q.y),
                1.0 - 2.0 * (q.y * q.y + q.z * q.z)
            )
            return x, y, yaw
        except Exception:
            return None

    # ── 공통 헬퍼 ────────────────────────────────────────

    def _stop_robot(self):
        cmd = Twist()
        cmd.linear.x = 0.0
        cmd.angular.z = 0.0
        self.cmd_pub.publish(cmd)
        self.prev_linear = 0.0
        self.prev_angular = 0.0

    @staticmethod
    def _dist(a, b):
        return math.hypot(a[0] - b[0], a[1] - b[1])

    @staticmethod
    def _normalize_angle(a):
        while a >  math.pi: a -= 2 * math.pi
        while a < -math.pi: a += 2 * math.pi
        return a

    @staticmethod
    def _clamp(v, lo, hi):
        return max(lo, min(hi, v))

    @staticmethod
    def _limit_step(target, prev, step):
        if target > prev + step: return prev + step
        if target < prev - step: return prev - step
        return target


def main():
    rclpy.init()
    node = LimoPurePursuit()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node._stop_robot()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
