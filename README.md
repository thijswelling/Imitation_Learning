## Command Cheatsheet

### 1. Teleoperation Protocol

* Open a terminal and set up your workspace:
```bash
cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash
./start_c1.sh 192.168.0.102

```


* Press the start button on the UR3e Teach Pendant.
* Press **`e`** to align the Omni pen with the UR3e gripper and start teleoperation.
* **Keyboard controls:**
* **Spacebar:** Clutch (disengage connection)
* **`r`:** Bring robot to home position
* **`c`:** Close gripper
* **`o`:** Open gripper



---

### 2. Record Protocol

* **Terminal 1:** Start teleoperation following the steps above.
* **Terminal 2:** Start the trial logger:
```bash
cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash
ros2 run ur3e_teleop_control trial_logger

```


* **Back in Terminal 1:**
* Press **`r`** for the home position.
* Press **`e`** to start teleoperation.
* Press **`1`** to start recording the CSV.
* Perform the demonstration.
* Press **`2`** to stop recording.
* Press **`r`** to return home.
* *Repeat this about 50 times (poor demonstrations will be automatically filtered out).*



---

### 3. Create Usable Dataset

```bash
cd ~/ros2_ws
rm -rf ~/ur3e_datasets/key_in_tube
python3 ./create_dataset.py

```

---

### 4. Train Algorithm

```bash
cd ~/ros2_ws/lerobot_source
python3 src/lerobot/scripts/lerobot_train.py \
  --policy.type=diffusion \
  --policy.device="cuda" \
  --dataset.repo_id="thijs/key_in_tube" \
  --dataset.root="/home/thijs/ur3e_datasets/key_in_tube" \
  --output_dir="/home/thijs/outputs/diffusion_ur3e" \
  --batch_size=32 \
  --steps=15000 \
  --policy.horizon=16 \
  --policy.n_action_steps=8 \
  --policy.n_obs_steps=2 \
  --policy.down_dims="[128, 256, 512]" \
  --policy.push_to_hub=false \
  --wandb.enable=false \
  --dataset.streaming=false

```

---

### 5. Deployment / Autonomous Execution

* **Terminal 1 (Driver & Controller):**
```bash
cd ~/ros2_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 launch ur_robot_driver ur_control.launch.py \
  ur_type:=ur3e \
  robot_ip:=192.168.0.102 \
  launch_rviz:=false \
  initial_joint_controller:=scaled_joint_trajectory_controller

```


*(Press **[PLAY]** on the UR Teach Pendant for External Control).*
* **Terminal 2 (AI Inference Node):**
```bash
cd ~/ros2_ws
colcon build --symlink-install
source /opt/ros/humble/setup.bash
source install/setup.bash
export PYTHONPATH=$PYTHONPATH:~/ros2_ws/lerobot_source/src

ros2 run ur3e_teleop_control inference_node

```
