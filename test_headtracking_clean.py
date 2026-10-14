#!/usr/bin/env python3
import cv2
import numpy as np
import ctypes
import math
import time
import sys

# --- NIEUW: ROS 2 imports voor toetsenbord-forwarding ---
import rclpy
from std_msgs.msg import String

# Init ROS 2 netwerk voor het VR-script
rclpy.init()
vr_node = rclpy.create_node('vr_headtracking_node')
key_pub = vr_node.create_publisher(String, '/vr_keyboard', 10)

# --- 1. OpenHMD DK2 IMU Setup ---
try:
    lib = ctypes.CDLL("libopenhmd.so.0")
except OSError:
    lib = ctypes.CDLL("libopenhmd.so")

class ohmd_context(ctypes.Structure): pass
class ohmd_device(ctypes.Structure): pass

lib.ohmd_ctx_create.restype = ctypes.POINTER(ohmd_context)
lib.ohmd_ctx_destroy.argtypes = [ctypes.POINTER(ohmd_context)]
lib.ohmd_ctx_probe.argtypes = [ctypes.POINTER(ohmd_context)]
lib.ohmd_ctx_probe.restype = ctypes.c_int
lib.ohmd_ctx_update.argtypes = [ctypes.POINTER(ohmd_context)]
lib.ohmd_list_open_device.argtypes = [ctypes.POINTER(ohmd_context), ctypes.c_int]
lib.ohmd_list_open_device.restype = ctypes.POINTER(ohmd_device)
lib.ohmd_device_getf.argtypes = [ctypes.POINTER(ohmd_device), ctypes.c_int, ctypes.POINTER(ctypes.c_float)]
lib.ohmd_device_getf.restype = ctypes.c_int

OHMD_ROTATION_QUAT = 1

ctx = lib.ohmd_ctx_create()
if lib.ohmd_ctx_probe(ctx) <= 0:
    print("[FOUT] Geen Oculus DK2 IMU gevonden via USB!")
    lib.ohmd_ctx_destroy(ctx)
    exit(1)

hmd = lib.ohmd_list_open_device(ctx, 0)
quat = (ctypes.c_float * 4)()

def get_head_angles():
    lib.ohmd_ctx_update(ctx)
    lib.ohmd_device_getf(hmd, OHMD_ROTATION_QUAT, quat)
    x, y, z, w = quat[0], quat[1], quat[2], quat[3]
    
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    pitch = math.degrees(math.atan2(sinr_cosp, cosr_cosp))

    siny_cosp = 2 * (w * y - z * x)
    yaw = math.degrees(math.asin(max(-1.0, min(1.0, siny_cosp))))
    return pitch, yaw

# --- 2. Camera Initialisatie ---
cam_idx = 7  # Standaard fallback
if "--cam" in sys.argv:
    try:
        idx_pos = sys.argv.index("--cam") + 1
        cam_idx = int(sys.argv[idx_pos])
    except (IndexError, ValueError):
        pass

print(f"Logitech BRIO openen op /dev/video{cam_idx}...")
cap = cv2.VideoCapture(cam_idx, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
cap.set(cv2.CAP_PROP_FPS, 30)

connected = False
for _ in range(15):
    ret, frame = cap.read()
    if ret and frame is not None:
        connected = True
        break
    time.sleep(0.1)

if not connected:
    print("[FOUT] Kon geen videoframes lezen.")
    exit(1)

h_in, w_in = frame.shape[:2]
print(f"[OK] Stream actief: {w_in}x{h_in}")

# --- 3. Zoom & Tracking Parameters ---
zoom_factor = 0.70
sensitivity = 7.0

# --- 4. Window Setup voor DK2 ---
win_name = "DK2_Clean_Test"
cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
cv2.resizeWindow(win_name, 1080, 1920)
cv2.moveWindow(win_name, 1920, 0)

base_pitch, base_yaw = get_head_angles()

print("=" * 60)
print("ALLES-IN-ÉÉN BEDIENING (Zorg dat het VR-venster actief is!):")
print("- Pijltje OMHOOG/OMLAAG : Camera In/Uitzoomen")
print("- Pijltje LINKS         : VR Centreren (nulpunt reset)")
print("- Spatiebalk            : Robot Clutch Aan/Uit")
print("- Toets 'e'             : Robot Engage")
print("- Toets 'c' / 'o'       : Gripper Sluiten / Openen")
print("- Toets 'r'             : Robot Reset")
print("- Toets 'q'             : Afsluiten")
print("=" * 60)

KEY_UP = (82, 65362)
KEY_DOWN = (84, 65364)
KEY_LEFT = (81, 65361)

while True:
    ret, frame = cap.read()
    if not ret:
        continue

    pitch, yaw = get_head_angles()
    d_yaw = yaw - base_yaw
    d_pitch = pitch - base_pitch

    crop_w = int(w_in * zoom_factor)
    crop_h = int(h_in * zoom_factor)

    cx = int((w_in / 2) - (d_yaw * sensitivity))
    cy = int((h_in / 2) - (d_pitch * sensitivity))

    x1 = max(0, min(cx - crop_w // 2, w_in - crop_w))
    y1 = max(0, min(cy - crop_h // 2, h_in - crop_h))
    
    cropped = frame[y1:y1 + crop_h, x1:x1 + crop_w]
    eye = cv2.resize(cropped, (960, 1080))
    sbs = np.hstack((eye, eye))
    final_frame = cv2.rotate(sbs, cv2.ROTATE_90_COUNTERCLOCKWISE)

    cv2.imshow(win_name, final_frame)
    key = cv2.waitKeyEx(1)

    if key == ord('q'):
        break
    elif key in KEY_LEFT:
        base_pitch, base_yaw = get_head_angles()
        print(f"[Centreren] Pitch: {base_pitch:.1f}°, Yaw: {base_yaw:.1f}°")
    elif key in KEY_UP:
        zoom_factor = max(0.30, zoom_factor - 0.05)
        print(f"[Zoom In] Factor: {1.0/zoom_factor:.1f}x")
    elif key in KEY_DOWN:
        zoom_factor = min(1.00, zoom_factor + 0.05)
        print(f"[Zoom Uit] Factor: {1.0/zoom_factor:.1f}x")
    
    # --- NIEUW: Robot besturing doorsturen via ROS ---
    elif key in [ord('e'), ord('c'), ord('o'), ord('r'), ord(' ')]:
        char_key = chr(key)
        msg = String(data=char_key)
        key_pub.publish(msg)
        print(f"[VR Window] Robot-commando verzonden: '{char_key}'")

cap.release()
lib.ohmd_ctx_destroy(ctx)
cv2.destroyAllWindows()
vr_node.destroy_node()
rclpy.shutdown()