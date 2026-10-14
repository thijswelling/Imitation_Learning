import os
import glob
import gc
import time
import numpy as np
import pandas as pd
import torch
from lerobot.datasets.lerobot_dataset import LeRobotDataset

data_dir = os.path.expanduser("~/teleop_experiment_data")
local_dataset_dir = os.path.expanduser("~/ur3e_datasets/key_in_tube")
task_name = "Key insertion task"

csv_files = sorted(glob.glob(os.path.join(data_dir, "trial_*.csv")))
if not csv_files:
    print("Geen CSV bestanden gevonden in", data_dir)
    exit()

required_cols = {'j1', 'j2', 'j3', 'j4', 'j5', 'j6', 'Fx', 'Fy', 'Fz', 'Mx', 'My', 'Mz', 'tcp_x', 'tcp_y', 'tcp_z'}

# --- STAP 1: Analyseer alle trials om slechte pogingen (outliers) te filteren ---
trial_summaries = []
for file in csv_files:
    df = pd.read_csv(file)
    if not required_cols.issubset(set(df.columns)) or len(df) < 100:
        continue
    end_tcp = df.iloc[-10:][['tcp_x', 'tcp_y', 'tcp_z']].mean().values
    trial_summaries.append((file, df, end_tcp, len(df)))

# Bereken het mediane eindpunt (het 'echte' midden van de buis) en mediane duur
all_end_tcps = np.array([t[2] for t in trial_summaries])
median_end_tcp = np.median(all_end_tcps, axis=0)
median_len = np.median([t[3] for t in trial_summaries])

print(f"Mediaan eindpunt (TCP x,y,z): {np.round(median_end_tcp, 4)} | Mediane lengte: {int(median_len)} rijen")

# --- STAP 2: Maak LeRobot Dataset aan ---
dataset = LeRobotDataset.create(
    repo_id="thijs/key_in_tube",
    root=local_dataset_dir,
    fps=50,
    robot_type="ur3e",
    features={
        "observation.state": {
            "dtype": "float32",
            "shape": (6,),
            "names": ["j1", "j2", "j3", "j4", "j5", "j6"]
        },
        "observation.environment_state": {
            "dtype": "float32",
            "shape": (6,),
            "names": ["Fx", "Fy", "Fz", "Mx", "My", "Mz"]
        },
        "action": {
            "dtype": "float32",
            "shape": (6,),
            "names": ["target_j1", "target_j2", "target_j3", "target_j4", "target_j5", "target_j6"]
        },
    }
)

valid_episodes = 0
lookahead = 2  # Voorspel de gewrichtshoek 2 frames (40 ms) vooruit voor een strakker stuursignaal

for file, df, end_tcp, length in trial_summaries:
    dist_from_median = np.linalg.norm(end_tcp - median_end_tcp)
    
    # Filter: sla trials over die > 1.2 cm naast het mediane doel eindigen of > 1.6x zo lang duren
    if dist_from_median > 0.012:
        print(f"❌ Overslaan {os.path.basename(file)}: Eindpunt wijkt {dist_from_median*1000:.1f} mm af.")
        continue
    if length > median_len * 1.6:
        print(f"❌ Overslaan {os.path.basename(file)}: Duurde te lang ({length} rijen, mogelijk gehaperd).")
        continue

    # Auto-Tare: Bereken de nul-offset van de F/T sensor uit de eerste 15 rust-samples van deze trial
    wrench_cols = ['Fx', 'Fy', 'Fz', 'Mx', 'My', 'Mz']
    tare_offset = df.iloc[:15][wrench_cols].mean().values.astype("float32")

    states_df = df.iloc[:-lookahead].reset_index(drop=True)
    actions_df = df.iloc[lookahead:].reset_index(drop=True)
    
    for t in range(len(states_df)):
        current_joints = states_df.loc[t, ['j1', 'j2', 'j3', 'j4', 'j5', 'j6']].values.astype("float32")
        
        # Netto krachten én momenten (gecorrigeerd voor sensor-drift)
        raw_wrench = states_df.loc[t, wrench_cols].values.astype("float32")
        net_wrench = raw_wrench - tare_offset
        
        target_joints = actions_df.loc[t, ['j1', 'j2', 'j3', 'j4', 'j5', 'j6']].values.astype("float32")

        dataset.add_frame({
            "observation.state": torch.tensor(current_joints, dtype=torch.float32),
            "observation.environment_state": torch.tensor(net_wrench, dtype=torch.float32),
            "action": torch.tensor(target_joints, dtype=torch.float32),
            "task": task_name,
        })
    
    dataset.save_episode()
    valid_episodes += 1
    print(f"✅ Toegevoegd: {os.path.basename(file)} (afwijking einddoel: {dist_from_median*1000:.1f} mm)")

del dataset
gc.collect()
time.sleep(2)
print(f"\n🎯 Klaar! {valid_episodes} strakke trials opgeslagen in: {local_dataset_dir}")