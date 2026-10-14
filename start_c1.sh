#!/usr/bin/env bash
# FORCE FEEDBACK + DIRECT VIEW

if [ -z "$1" ]; then
    echo "Usage: ./start_teleop.sh <ROBOT_IP>"
    exit 1
fi

ROBOT_IP=$1
WS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source /opt/ros/humble/setup.bash
source "${WS_DIR}/install/setup.bash"

echo "=== Starting Teleop for UR3e on IP: ${ROBOT_IP} ==="

cleanup() {
    echo -e "\nShutting down teleop pipeline..."
    kill $(jobs -p) 2>/dev/null
    wait $(jobs -p) 2>/dev/null
    echo "All nodes safely terminated."
}
trap cleanup SIGINT SIGTERM EXIT

# 1. Start the UR Robot Driver (Background)
ros2 launch ur_robot_driver ur_control.launch.py ur_type:=ur3e robot_ip:=${ROBOT_IP} launch_rviz:=false initial_joint_controller:=forward_velocity_controller &
sleep 5 

# 2. Start the Robotiq Gripper (Background)
ros2 run ur3e_teleop_control robotiq_bridge --ros-args -p robot_ip:=${ROBOT_IP} &
sleep 2

# 3. Start de Task Space Controller (Verwerkt jouw input naar snelheden)
ros2 run ur3e_teleop_control task_space_controller &
sleep 1

# 4. Start the Haptic Bridge
ros2 run touch_haptics touch_haptic_bridge &
sleep 2

# 5. Start Haptic Publisher mét Force Feedback (IN DE FOREGROUND)
echo "Haptische besturing geactiveerd. Druk op Ctrl+C om te stoppen."
ros2 run ur3e_teleop_control touch_publisher --ros-args -p enable_force_feedback:=true