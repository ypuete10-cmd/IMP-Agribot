# Pi 5 Command Reference — AgriBot

Yvette Lee EnQi (25034155) · Last updated: 29 October 2026

---

## Table of Contents

1. [SSH & Network](#1-ssh--network)
2. [Git Workflow](#2-git-workflow)
3. [System Config](#3-system-config)
4. [Python Environment](#4-python-environment)
5. [ROS2 Workspace](#5-ros2-workspace)
6. [Model Files](#6-model-files)
7. [AI Inference](#7-ai-inference)
8. [One-Command Bringup](#8-one-command-bringup)
9. [Motors + Encoders](#9-motors--encoders)
10. [Sensors (IMU + GPS + Environment)](#10-sensors-imu--gps--environment)
11. [Mission Control Dashboard](#11-mission-control-dashboard)
12. [Web Drive Control](#12-web-drive-control)
13. [EKF + Waypoint Navigation](#13-ekf--waypoint-navigation)
14. [Ultrasonic Emergency Stop](#14-ultrasonic-emergency-stop)
15. [Quick Fixes](#15-quick-fixes)
16. [File Locations](#16-file-locations)
17. [Status Snapshot](#17-status-snapshot)
18. [Emergency Stop v2 (22 Oct)](#18-emergency-stop-v2-22-oct)
19. [Known Issues & Next Steps](#19-known-issues--next-steps)
20. [AI-Waypoint Integration (28 Oct)](#20-ai-waypoint-integration-28-oct)
21. [Working Autonomous Nav (29 Oct)](#21-working-autonomous-nav-29-oct)

---

## 1. SSH & Network

```bash
ssh yvette_pi@192.168.x.x
# or hostname if mDNS works
ssh yvette_pi@raspberrypi.local
```

---

## 2. Git Workflow

```bash
cd ~/ros2_ws/src/robot_control
git status
git add .
git commit -m "message"
git pull origin main
git push origin main
```

If rejected:
```bash
git config pull.rebase false
git pull origin main
git push origin main
```

---

## 3. System Config

**Enable UART (GPS) — both lines required on Pi 5 + Ubuntu 24.04:**
```bash
sudo nano /boot/firmware/config.txt
# Add:
enable_uart=1
dtparam=uart0=on
```

Remove serial console from cmdline:
```bash
sudo nano /boot/firmware/cmdline.txt
# Remove: console=serial0,115200
```

Add user to dialout:
```bash
sudo usermod -aG dialout $USER
# Log out and back in for group change to take effect
```

---

## 4. Python Environment

```bash
# TFLite runtime
pip install ai-edge-litert numpy==1.26.4

# ROS2 + sensor deps
sudo apt install python3-rpi-lgpio python3-smbus2
pip install pyserial

# Dashboard
pip install flask requests
```

---

## 5. ROS2 Workspace

```bash
cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash

# Verify package
ros2 pkg list | grep robot_control

# Source in every new terminal
source ~/ros2_ws/install/setup.bash
```

---

## 6. Model Files

| File | Path |
|------|------|
| TFLite model | `models/plant_health.tflite` |
| Class names | `models/class_names.json` |

---

## 7. AI Inference

```bash
# Single capture + classify (legacy manual mode)
ros2 run robot_control capture

# Event-driven AI node (waypoint-triggered)
ros2 run robot_control ai_inference

# Verify topic
ros2 topic echo /plant_health
ros2 topic echo /waypoint/scan_done
```

---

## 8. One-Command Bringup

**Starts 10 processes:**
```bash
cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash
ros2 launch robot_control bringup.launch.py
```

Processes launched:
- `motor_driver` — PWM differential drive + emergency cut-off + watchdog latch
- `encoder_node` — 4-wheel encoders + odometry + TF
- `imu_node` — BNO055 I2C IMU, 20 Hz
- `env_node` — AHT30 temp/humidity
- `gps_node` — NEO-8M UART GPS, 1 Hz
- `ekf_filter_node` — robot_localization EKF (5 Hz)
- `navsat_transform_node` — GPS pipeline (standby for outdoor)
- `waypoint_follower` — indoor autonomous nav, pause-resume + scan handshake
- `ultrasonic_node` — 2× HC-SR04 emergency stop
- `ai_inference` — event-driven TFLite scanner
- `rosbridge_server` — WebSocket bridge
- `camera_stream` — Flask MJPEG (port 5000) + frame sharing to `/tmp/latest_frame.jpg`

**Dashboard (second terminal):**
```bash
python3 ~/ros2_ws/src/robot_control/dashboard/app.py
```

**Access:**
- Mission Control: `http://[PI_IP]:8080`
- Camera only: `http://[PI_IP]:5000`
- Drive page: `http://[PI_IP]:5000/control`

---

## 9. Motors + Encoders

**Motor settings (in `motor_driver.py`):**
- `max_speed = 0.8`
- `wheel_separation = 0.18`
- `min_pwm = 0.5` (was 0.25 — increased for static friction)

**Watchdog latch:**
- `watchdog_callback()` uses `self.watchdog_triggered` flag
- Only stops motors **ONCE** on timeout, resets on new `/cmd_vel`
- Prevents watchdog from continuously overwriting autonomous commands

**Kill orphaned motor process:**
```bash
pkill -f motor_driver
```

**Test motors:**
```bash
# Install if not present
sudo apt install ros-jazzy-teleop-twist-keyboard
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

**Encoder topics:**
```bash
ros2 topic echo /wheel_ticks
ros2 topic echo /odom
```

---

## 10. Sensors (IMU + GPS + Environment)

**IMU:**
```bash
ros2 topic echo /imu/data
# Check chip ID
i2cdetect -y 1
```

**GPS:**
```bash
ros2 topic echo /fix
# Raw UART
cat /dev/ttyAMA0
```

**Environment:**
```bash
ros2 topic echo /env/temperature
ros2 topic echo /env/humidity
```

---

## 11. Mission Control Dashboard

**Port:** 8080

**Features:**
- Live sensor cards (GPS, odom, heading, env, AI scan)
- Embedded camera feed + drive pad
- Keyboard WASD + Arrow keys (publish /cmd_vel at 10 Hz)
- Waypoint buttons: Save, Clear, Run, Stop
- GPS health map (Leaflet + OpenStreetMap)
- Results table

**All sensor data via roslib.js over rosbridge WebSocket (port 9090).**
**Throttle rates:** `/imu/data` at 10 Hz, `/odom` at 4 Hz to prevent
rosbridge "Write queue full" warnings.

---

## 12. Web Drive Control

**Embedded in dashboard + standalone at `/control`.**

- WASD / Arrow keys + speed slider
- Auto-stop on release / blur
- roslib.js → WebSocket → rosbridge → /cmd_vel at 10 Hz
- `autonomous` flag prevents dashboard zeros during waypoint Run

**⚠️ Multi-tab warning:** Multiple dashboard tabs both publish /cmd_vel
zeros at 10 Hz, which can cancel follower drive commands. Use **only one
dashboard tab** during autonomous Run.

---

## 13. EKF + Waypoint Navigation

**EKF:**
```bash
ros2 topic echo /odometry/filtered
```

Config: `config/ekf.yaml`
- `two_d_mode: true`
- `world_frame: odom`
- `odom0` = /odom (x, y, vx, yaw_vel)
- `imu0` = /imu/data (yaw, yaw_rate, differential)
- `frequency: 5.0` (was 20.0 — reduced to prevent Pi 5 overload)

**Waypoint follower topics:**
```bash
ros2 topic pub /waypoint/save std_msgs/Empty {}
ros2 topic pub /waypoint/clear std_msgs/Empty {}
ros2 topic pub /waypoint/run std_msgs/Empty {}
ros2 topic pub /waypoint/stop std_msgs/Empty {}
```

**Scan handshake topics:**
```bash
ros2 topic echo /waypoint/reached       # Float32MultiArray [idx, x, y]
ros2 topic echo /waypoint/scan_done     # Empty
```

**Parameters:**
- Turn-in-place threshold: `|yaw_err| > 0.8 rad` (was 0.5)
- Forward speed: `0.3 * dist` capped at `0.3 m/s` (was 0.15)
- Angular cap: `±0.3 rad/s`
- Position tolerance: `15 cm`
- Orientation tolerance: `0.15 rad`
- Scan freeze: waits for `/waypoint/scan_done` before resuming

---

## 14. Ultrasonic Emergency Stop

**Topics:**
```bash
ros2 topic echo /ultrasonic/front    # Float32, minimum distance (m)
ros2 topic echo /emergency_stop      # Bool, True when < threshold
```

**Hardware:**
- 2× HC-SR04 front sensors, angled inward
- Trig: GPIO 17 / 23
- Echo: GPIO 22 / 27 (with 1kΩ + 2kΩ voltage dividers)
- `lgpio` backend, `gpiochip 4` (Pi 5)

**Threshold:** 10 cm (configurable via `THRESHOLD_CM` in node)

---

## 15. Quick Fixes

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: 'std_msg'` | `std_msgs` (with 's') |
| `NameError: name 'requests' is not defined` | Check `import requests` in `app.py`; verify with `grep` |
| `TypeError: 'function' object is not iterable` | `stream_with_context(gen())` (add parens) |
| Camera iframe 404 | Check for stray quote in `src` attribute |
| Browser cache stale | Incognito + Ctrl+Shift+R |
| Port 8080 blocked | `pkill -f app.py` then `curl -I localhost:8080` |
| GPIO busy | `pkill -f <node_name>` before relaunch |
| `gpiochip_open(0)` fails on Pi 5 | Use `gpiochip_open(4)` |
| Waypoints "not saving" | Check `self.emergency` defined in `__init__` |
| Dashboard/waypoint cmd_vel conflict | `autonomous` flag in dashboard JS |
| **Run starts but robot doesn't move** | Check single dashboard tab; verify QoS with `ros2 topic info /cmd_vel --verbose` |
| **Robot moves when lifted but not on floor** | Check `min_pwm` ≥ 0.5; check watchdog not latching |
| **Robot stops after manual drive, won't Run** | Watchdog latch — `watchdog_triggered` flag must reset on new cmd_vel |
| **Scan skipped at last waypoint** | Scan trigger must run for ALL waypoints; mission-complete in `scan_done_cb` |
| **EKF "Failed to meet update rate"** | Reduce `frequency` in `ekf.yaml` to 5.0 |
| QoS mismatch (silent drop) | Explicit `QoSProfile(RELIABLE, VOLATILE, KEEP_LAST/10)` on both pub and sub |
| rosbridge "Write queue full" | Add `throttle_rate` to heavy topic subscriptions |

---

## 16. File Locations

| File | Path |
|------|------|
| Workspace | `~/ros2_ws/` |
| Package source | `~/ros2_ws/src/robot_control/` |
| Bringup launch | `launch/bringup.launch.py` |
| EKF config | `config/ekf.yaml` |
| Motor driver | `robot_control/motor_driver.py` |
| Encoder node | `robot_control/encoder_node.py` |
| IMU node | `robot_control/imu_node.py` |
| GPS node | `robot_control/gps_node.py` |
| Env node | `robot_control/env_node.py` |
| Waypoint follower | `robot_control/waypoint_follower.py` |
| Ultrasonic node | `robot_control/ultrasonic_node.py` |
| AI inference | `robot_control/ai_inference.py` |
| Camera stream | `robot_control/camera_stream.py` |
| Dashboard app | `dashboard/app.py` |
| Dashboard HTML | `dashboard/templates/index.html` |
| Drive page | `dashboard/drive/control.html` |
| AI model | `models/plant_health.tflite` |
| Waypoint JSON | `waypoints.json` |
| Results log | `dashboard/data/results.json` |
| Shared frame | `/tmp/latest_frame.jpg` |

---

## 17. Status Snapshot (29 Oct 2026)

| Component | Status |
|-----------|--------|
| Pi 5 + Ubuntu 24.04 + ROS2 Jazzy | Working |
| USB Webcam + V4L2 | Working |
| 4-wheel drive (dual L298N) | Working |
| 4× encoders + odometry | Working |
| BNO055 IMU (I2C, NDOF) | Working |
| NEO-8M GPS (UART) | Working (stream); fix needs sky view |
| AHT30 temp/humidity | Working |
| EKF (robot_localization) | Working (5 Hz) |
| Indoor waypoint navigation | Working |
| Ultrasonic emergency stop v2 | Working (motor-level cut-off, pause-resume) |
| AI-waypoint integration | Working (event-driven, scan handshake) |
| **End-to-end autonomous mission** | **VERIFIED** |
| Mission Control dashboard | Working |
| Web drive control | Working |
| AI inference (TFLite) | Working |
| One-command bringup (10 processes) | Working |
| QoS fix (/cmd_vel compatibility) | Working |
| Watchdog latch fix | Working |
| Camera lag reduction | Pending |
| ADS1115 battery monitor | Pending |
| Field-test waypoint accuracy | Pending |
| Report + slides | Pending |

---

## 18. Emergency Stop v2 (22 Oct)

### Architecture

```
/ultrasonic/front  →  ultrasonic_node  →  /emergency_stop
                                              ↓
                    ┌─────────────────────────┘
                    ↓
        motor_driver.py          waypoint_follower.py
        (motor-level cut-off)    (pause-resume, keeps index)
```

### Motor-Level Cut-Off

In `motor_driver.py` `cmd_vel_callback`:
```python
if self.emergency_active:
    left_pwm = right_pwm = 0.0
    # Motors zeroed regardless of cmd_vel source
```

This is the **last possible safety point** — catches drive pad, keyboard,
waypoint follower, and any other /cmd_vel publisher.

### Pause-Resume Waypoint Follower

- Emergency active → freeze motors, **keep `running=True`**, keep waypoint index
- Emergency clears → **auto-resume** driving toward same waypoint
- No need to press Run again after obstacle removal

### Ultrasonic Noise Filtering

| Technique | Purpose |
|-----------|---------|
| Staggered pings (+20ms) | Eliminate cross-talk between 2 sensors |
| Median-of-3 sampling | Reject single outliers |
| 5-reading debounce (~0.5s) | Require sustained obstacle before stop |
| 2cm minimum filter | Reject HC-SR04 glitches below physical minimum |

### Configuration

```python
THRESHOLD_CM = 10   # Indoor testing; raise for outdoor
```

---

## 19. Known Issues & Next Steps

### Known Issues

1. **Debug logging is verbose** — WP/CMD spam in terminal. Remove before demo.
2. **Camera lag** — 1080p @ 30 fps overloads Pi. Next: 640×480 @ 15 fps.
3. **Encoder drift** — ±10% per-leg without GPS loop closure
4. **IMU tilt** — BNO055 mounted ~18° off horizontal; remount before outdoor demo
5. **GPS no fix indoors** — expected; navsat transform ready for outdoor
6. **LCD moiré** — phone-screen leaves misclassify; use printed/real leaves
7. **Arrival tolerance** — 15 cm may need 20 cm for floor reliability

### Next Steps

| Priority | Task |
|----------|------|
| 1 | Multi-waypoint mission with scan at each |
| 2 | Camera lag reduction (640×480 @ 15 fps) |
| 3 | Remove debug logging |
| 4 | Tune arrival tolerance (15→20 cm if needed) |
| 5 | Field-test waypoint accuracy on actual floor |
| 6 | ADS1115 battery monitor (when LiPo returns) |
| 7 | Report writing + documentation |
| 8 | Slides (due 30 Nov) |
| 9 | Viva (2 Dec 2026) |

---

## 20. AI-Waypoint Integration (28 Oct)

### Architecture

```
waypoint_follower        ai_inference
       │                       ▲
       │  /waypoint/reached   │
       └──────────────────────┘
              [idx, x, y]
              (Float32MultiArray)

       ┌──────────────────────┐
       │  /waypoint/scan_done │
       └──────────────────────┘
              (Empty)
```

### Flow

1. **Waypoint follower** reaches waypoint (within 15 cm tolerance)
2. Publishes `/waypoint/reached` with `[idx, x, y]`
3. Sets `self.scanning = True` — motion frozen
4. **AI inference** receives trigger, grabs `/tmp/latest_frame.jpg`
5. Classifies with TFLite → publishes `/plant_health` + `/waypoint/scan_done`
6. Appends result to `results.json` (atomic: write tmp → `os.replace`)
7. **Waypoint follower** receives `/waypoint/scan_done`
8. Sets `self.scanning = False` — auto-resumes to next waypoint

### Frame Sharing

`camera_stream.py` writes every captured frame to `/tmp/latest_frame.jpg`:
- Avoids camera device contention (only `camera_stream` opens `/dev/video0`)
- AI node reads the file synchronously on trigger
- Single `camera.read()` per loop (no duplicate reads)

### Results JSON (Atomic Write)

```python
# ai_inference.py
with open(tmp_path, 'w') as f:
    json.dump(results, f)
os.replace(tmp_path, RESULTS_PATH)
```

Prevents Flask from reading partial JSON during concurrent write.

### QoS Fix (CRITICAL)

**Root cause:** After reboot, `waypoint_follower` defaulted to
`TRANSIENT_LOCAL` durability on `/cmd_vel` publisher. `motor_driver`
used `VOLATILE`. ROS2 silently dropped all messages — no errors,
no crashes, robot idle.

**Fix:** Explicit matching QoS on both sides:
```python
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy

qos = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=10
)
# Publisher (waypoint_follower)
cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', qos)
# Subscriber (motor_driver)
cmd_vel_sub = self.create_subscription(Twist, '/cmd_vel', callback, qos)
```

**Verify:**
```bash
ros2 topic info /cmd_vel --verbose
# Expect: Publisher count: 2, Subscription count: 2
# Both with RELIABLE reliability + VOLATILE durability
```

### Debug Checklist (Run → No Motion)

```bash
# 1. Confirm follower publishes commands
ros2 topic echo /cmd_vel --once

# 2. Check publish rate
timeout 3 ros2 topic hz /cmd_vel

# 3. Verify QoS compatibility
ros2 topic info /cmd_vel --verbose

# 4. Check for multi-tab dashboard zeros
# Close all browser tabs except one Mission Control tab

# 5. Check motor driver is alive
ros2 node list | grep motor

# 6. Check emergency stop is not latched
ros2 topic echo /emergency_stop --once
```

---

## 21. Working Autonomous Nav (29 Oct)

### 5 Critical Bugs Fixed

#### 1. Motor Driver Watchdog Latch

**Symptom:** Robot only moved when lifted off floor; worked on first run
after boot but not after manual drive.

**Cause:** `watchdog_callback()` ran every 1 s and **continuously** zeroed
motors. After manual drive stopped, watchdog fired and kept overwriting
motor speeds to `0.0` even when autonomous `/cmd_vel` commands arrived.

**Fix:** Added `self.watchdog_triggered` flag:
```python
# In watchdog_callback:
if not self.watchdog_triggered:
    self.watchdog_triggered = True
    self.set_motor(0, 0)
    self.get_logger().warn("Watchdog: motors stopped (triggered)")

# In cmd_vel_callback:
self.watchdog_triggered = False  # Reset on new command
```

Watchdog only stops motors **ONCE** on timeout, resets when new `/cmd_vel`
arrives.

#### 2. QoS Durability Mismatch

Already documented in Section 20. Confirmed as root cause of "Run does
nothing" after reboot.

#### 3. AI Scan Never Triggered (Logic Bug)

**Symptom:** Robot reached waypoint but jumped to "All waypoints reached!"
without scanning.

**Cause:** Scan trigger only ran if `current_idx < len(waypoints)`. With 1
waypoint, `idx=1 == len=1`, so scan was skipped.

**Fix:** Trigger scan for **EVERY** waypoint including last. Move
mission-complete check to `scan_done_cb`:
```python
# OLD (broken):
if current_idx < len(waypoints):  # Skips last waypoint!
    trigger_scan()
else:
    mission_complete()

# NEW (fixed):
trigger_scan()  # Always scan at arrival

# In scan_done_cb:
if current_idx >= len(waypoints):
    mission_complete()
else:
    resume_to_next_waypoint()
```

#### 4. EKF Update Rate Too High

**Symptom:** `"Failed to meet update rate! Took 0.26s"`

**Cause:** `frequency: 20.0` in `ekf.yaml` too demanding for Pi 5 with
10 nodes + camera + AI.

**Fix:** `config/ekf.yaml`:
```yaml
frequency: 5.0  # Was 20.0
```

#### 5. Follower Drive Parameters Too Weak

**Symptom:** Wheels turned when lifted but not on floor (insufficient torque).

**Cause:** `lin=0.15` max and `min_pwm=0.25` too low for static friction.

**Fix:** `waypoint_follower.py` + `motor_driver.py`:
```python
# Follower:
lin_speed = min(0.3 * distance, 0.3)   # Was 0.15

# Motor driver:
min_pwm = 0.5                           # Was 0.25
```

Turn threshold also relaxed from `0.5 rad` → `0.8 rad` for smoother
forward motion.

### Verified End-to-End Mission

| Step | Status |
|------|--------|
| Run button pressed | ✅ "Autonomous run started: N waypoints" |
| Robot drives on floor | ✅ After watchdog fix |
| Slows near target | ✅ Proportional speed scaling |
| Stops within 15 cm | ✅ ~5 cm accuracy over 1 m |
| Publishes `/waypoint/reached` | ✅ AI receives trigger |
| AI classifies frame | ✅ `/plant_health` + `/waypoint/scan_done` |
| Robot resumes to next waypoint | ✅ After scan_done received |
| Emergency stop pauses | ✅ Freezes motion |
| Emergency clear resumes | ✅ Continues same waypoint |
| Mission complete | ✅ "All waypoints reached!" |

### Debug Infrastructure

Real-time logging format:
```
WP 0/1: pos=(0.74,0.56) yaw=0.92 | dist=0.06 yaw_err=-2.37
Watchdog: triggered (no cmd_vel for 1.0s)
Scan: reached WP-0, waiting for scan_done...
Scan: done received, resuming to WP-1
```

### Performance

| Metric | Value |
|--------|-------|
| Navigation accuracy | ~5 cm over 1 m distance |
| EKF output rate | 5 Hz (stable, no missed deadlines) |
| /cmd_vel publish rate | ~10 Hz during motion |
| Scan latency | ~2 s (TFLite inference + JSON write) |
| Mission sequence | Run → Drive → Arrive → Scan → Resume → Complete |

---

*Yvette Lee EnQi (25034155) — Graduation Project, 2026*
