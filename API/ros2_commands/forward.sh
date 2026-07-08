#!/bin/bash
source /opt/ros/humble/setup.bash 2>/dev/null
source /home/agilex/agilex_ws/install/setup.bash 2>/dev/null
ros2 topic pub --times 20 -r 10 --wait-matching-subscriptions 0 \
  /cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}'
