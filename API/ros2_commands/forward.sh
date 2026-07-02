#!/bin/bash
# 리모카(LIMO) 앞으로 이동 명령 (0.2 m/s, 2초간)
ros2 topic pub --times 20 /cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}'
