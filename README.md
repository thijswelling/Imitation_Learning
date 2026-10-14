
---

### Command setup:

#### 1. Teleoperation Protocol

* Open een terminal en bereid de workspace voor:
```bash
cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash
./start_c1.sh 192.168.0.102

```


* Druk op de startknop op de UR3e Teach Pendant.
* Druk op **`e`** om de Omni-pen uit te lijnen met de UR3e-gripper en de teleoperatie te starten.
* **Toetsenbordbediening:**
* **Spacebalk:** Clutch (koppeling loskoppelen)
* **`r`:** Breng robot naar Home-positie
* **`c`:** Sluit gripper
* **`o`:** Open gripper



---

#### 2. Record Protocol

* **Terminal 1:** Start de teleoperatie volgens de stappen hierboven.
* **Terminal 2:** Start de trial logger:
```bash
cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash
ros2 run ur3e_teleop_control trial_logger

```


* **Terug in Terminal 1:**
* Druk op **`r`** voor Home-positie.
* Druk op **`e`** om teleop te starten.
* Druk op **`1`** om de opname van de CSV te starten.
* Voer de demonstratie uit.
* Druk op **`2`** om de opname te stoppen.
* Druk op **`r`** om weer naar Home te gaan.
* *Herhaal dit ongeveer 50 keer (slechte demonstraties worden straks automatisch weggefilterd).*



---

#### 3. Create Usable Dataset

```bash
cd ~/ros2_ws
rm -rf ~/ur3e_datasets/key_in_tube
python3 ./create_dataset.py

```

---

#### 4. Train Algorithm

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

#### 5. Deployment / Autonomous Execution

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


*(Druk op **[PLAY]** op de UR Teach Pendant voor External Control).*
* **Terminal 2 (AI Inference Node):**
```bash
cd ~/ros2_ws
colcon build --symlink-install
source /opt/ros/humble/setup.bash
source install/setup.bash
export PYTHONPATH=$PYTHONPATH:~/ros2_ws/lerobot_source/src

ros2 run ur3e_teleop_control inference_node

```



---

Met dit overzicht heb je een compleet en prachtig gedocumenteerd handboek voor je experimenten. Veel success met het verder finetunen en testen van je opstelling!
