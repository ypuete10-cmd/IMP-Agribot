# Pi 5 Command Reference — AgriBot

Yvette Lee EnQi (25034155) · Last updated: 12 November 2026

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
22. [Manual AI Scan Mode (2 Nov)](#22-manual-ai-scan-mode-2-nov)
23. [Three Root Causes Fixed (10 Nov)](#23-three-root-causes-fixed-10-nov)
24. [AI Root Cause Closed — Model Retrained (12 Nov)](#24-ai-root-cause-closed--model-retrained-12-nov)

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
| **ChunkedEncodingError on camera** | Restart dashboard + browser refresh after bringup restart |
| **AI always returns same class** | Check normalization: must be `img / 127.5 - 1.0`, not raw uint8 |

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

## 17. Status Snapshot (2 Nov 2026)

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
| **Manual AI Scan Mode** | **Working** |
| **AI normalization fix** | **Working** ([-1, 1]) |
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
8. **Camera proxy ChunkedEncodingError** — restart dashboard + browser after
   bringup restart
9. **Turning power on carpet** — may need PWM increase for carpet surfaces

### Next Steps

| Priority | Task |
|----------|------|
| 1 | Multi-waypoint mission with scan at each |
| 2 | Camera lag reduction (640×480 @ 15 fps) |
| 3 | Remove debug logging |
| 4 | Tune arrival tolerance (15→20 cm if needed) |
| 5 | Field-test waypoint accuracy on actual floor |
| 6 | Turning power increase for carpet |
| 7 | ADS1115 battery monitor (when LiPo returns) |
| 8 | Report writing + documentation |
| 9 | Slides (due 30 Nov) |
| 10 | Viva (2 Dec 2026) |

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
| Manual scan | ~1–2 s via dashboard "Scan Plant" button |
| AI preprocessing | MobileNetV3: img / 127.5 - 1.0 (normalized [-1, 1]) |
| Mission sequence | Run → Drive → Arrive → Scan → Resume → Complete |

---

## 22. Manual AI Scan Mode (2 Nov)

### Overview

On-demand AI classification without waypoint setup. Drive robot manually to
any plant, click **"Scan Plant"** on the dashboard, and receive classification
results in 1–2 seconds.

### How It Works

1. User drives robot to target plant (WASD, arrow keys, or drive pad)
2. Clicks **"Scan Plant"** button on Mission Control dashboard
3. Dashboard publishes `/ai/scan_trigger` (`std_msgs/Empty`)
4. `ai_inference` node receives trigger, grabs `/tmp/latest_frame.jpg`
5. TFLite classification runs → publishes `/plant_health` (JSON string)
6. Dashboard updates **AI Last Scan** card + **Results Table**
7. Scan logged as `"WP-00"` (manual) in `results.json`

### Dashboard UI Changes

**Scan Plant button** (purple):
```html
<button id="scan-btn" onclick="triggerScan()">Scan Plant</button>
```

**Scan status indicator** (orange → green):
```javascript
// On click:
document.getElementById('scan-status').textContent = 'Scanning...';
document.getElementById('scan-status').className = 'badge orange';

// On result received:
document.getElementById('scan-status').textContent = 'Done';
document.getElementById('scan-status').className = 'badge green';
```

**Clear Log button**:
```javascript
fetch('/api/clear', {method: 'POST'})
  .then(() => { /* clear results table + reset AI Last Scan */ });
```

### AI Normalization Fix

**Before (broken):**
```python
# Raw uint8 [0, 255] fed directly to model
input_data = np.expand_dims(img, axis=0)  # WRONG
```

**After (fixed):**
```python
# MobileNetV3 standard: normalize to [-1, 1]
img = img.astype(np.float32)
img = img / 127.5 - 1.0
input_data = np.expand_dims(img, axis=0)  # CORRECT
```

**Impact:** Raw uint8 inputs were 100× scale, breaking softmax distribution.
After fix, class probabilities are properly distributed and accuracy improved.

### Debug Logging

```
Class probabilities: Tomato___Late_blight=0.932, Potato___Early_blight=0.041, ...
```

Added to `ai_inference.py` for real-time accuracy tuning.

### Quick Commands

```bash
# Trigger manual scan from terminal
ros2 topic pub /ai/scan_trigger std_msgs/msg/Empty {}

# Monitor classification result
ros2 topic echo /plant_health

# Check results.json
python3 -m json.tool ~/ros2_ws/src/robot_control/dashboard/data/results.json
```

### Files

| File | Change |
|------|--------|
| `ai_inference.py` | `manual_scan_cb`, normalization fix, debug logging |
| `index.html` | Scan Plant button, Clear Log button, status indicator |
| `app.py` | POST `/api/clear` endpoint |

---

## 23. Three Root Causes Fixed (10 Nov)

### Overview

Every "mystery" symptom traced to a concrete hardware or configuration cause
in one diagnostic session. Three independent root causes identified and fixed.

---

### Root Cause 1 — Motor PWM Floor Boost (navigation)

**Symptom:** Robot "randomly turning," heading estimate moving impossibly
fast, arcs during turn-in-place, driving away while believing aligned.

**Discovery:** WP debug log showed commanded `0.3 rad/s` but yaw changing at
`1.1–2.2 rad/s` (4–7×). The EKF was **correct** — the robot physically moved
that fast.

**Cause:** `min_pwm = 0.4` in `motor_driver.py` forces every nonzero motor
command to ≥40% duty. Gentle turns become motors at flat-out speed.

**Fix:**
```python
# motor_driver.py
self.min_pwm = 0.25  # was 0.4
```

**Lesson:** Verify actuator output before blaming estimators.

---

### Root Cause 2 — IMU Absolute Yaw Fused in EKF (navigation)

**Symptom:** Robot always turns when pressing Run, drives away from waypoint
while `yaw_err ≈ 0` (log: dist 2.19 → 4.47 at yaw_err -0.10).

**Cause:** `ekf.yaml` fused BNO055 **absolute yaw** (magnetometer-derived,
calib mag=0, motor-wire magnetic interference) mixed with encoder odometry.
Heading frame corrupted — encoder position and IMU heading in different frames.

**Fix:**
```yaml
# config/ekf.yaml
imu0_config: [false, false, false,
              false, false, false,  # orientation x,y,z — DISABLED
              false, false, false,
              true,  true,  true,   # angular velocity x,y,z (yaw rate only)
              false, false, false]
imu0_differential: false
```

Encoders now **own yaw** (self-consistent with position); IMU smooths yaw rate
only.

**Verification:**
```bash
# Run yaw_check.py — compare /odom vs /odometry/filtered yaw during hand-rotation
ros2 run robot_control yaw_check.py
```

---

### Root Cause 3 — Ultrasonic Sensors on 3.3V Rail (HARDWARE)

**Symptom:** Weeks of phantom obstacles, missed detections, idle OBSTACLE spam,
3–50 cm garbage at standstill, robot ran into a bag undetected.

**Cause:** HC-SR04 is a **5V sensor**; 3.3V rail starved the transmitter →
marginal/garbage echoes.

**Fix:**
1. VCC moved to **Pi 5V Pin 2** (echo dividers 1kΩ+2kΩ retained)
2. `>3.0 m` artifact filter in `measure()` kills timeout-boundary junk:
```python
# ultrasonic_node.py
dist = round(duration * 17150, 1)
if dist > 300.0:  # >3.0m = artifact (max real range ~2m)
    return None
```

**Verification:**
```bash
# Standalone test (no ROS, needs exclusive GPIO — stop bringup first)
python3 ~/ros2_ws/src/robot_control/test_ultrasonic.py
```

**Documented limitation:** Soft objects (bags, fabric) absorb ultrasound —
physics limitation of HC-SR04, not a wiring issue.

---

### Bugs Fixed (Same Session)

| # | Bug | Fix |
|---|-----|-----|
| 1 | Follower `IndexError` crash | Restored `not running/waypoints` guard + `current_idx` clamp |
| 2 | Manual-drive jerking | Follower publishes zeros **only when autonomous** (`self.autonomous` check) |
| 3 | Camera `/video_feed` 500 | Atomic write: `.jpg.tmp` → `_tmp.jpg` + `os.replace` (OpenCV codec selection) |
| 4 | Dashboard "0 waypoints" | New `/api/waypoints` Flask endpoint + live count |

---

### Dashboard v2 Rewrite

- **Nav Debug card:** live pos, yaw, dist, `yaw_err` to first waypoint
- **Live waypoint count:** `/api/waypoints`
- **Throttled subscriptions:** IMU 10 Hz, odom 4 Hz, env 2 Hz (prevents rosbridge queue overflow)

---

### Diagnostic Tools Added

| Tool | Command | Purpose |
|------|---------|---------|
| `yaw_check.py` | `ros2 run robot_control yaw_check.py` | Compare `/odom` vs `/odometry/filtered` yaw |
| `test_ultrasonic.py` | `python3 test_ultrasonic.py` | Standalone HC-SR04 test (stop bringup first) |
| WP/CMD debug log | Follower 10 Hz output | Primary diagnostic — dist, yaw_err, vx, vz |

---

### Verification Sequence (Post-Fix)

```bash
# 1. Reboot → single launch → gate check
ros2 launch robot_control bringup.launch.py

# 2. Dashboard green, wp-count live, Nav Debug card populated
# 3. Straight run: small stable yaw_err, monotonic dist decrease
# 4. Box test (solid obstacle): pause ~20cm, hold, resume on removal
# 5. AI screen test: dataset image on phone, tilted against glare
```

---

## 24. AI Root Cause Closed — Model Retrained (12 Nov)

### Diagnosis Summary

Multi-day investigation concluded: **the original model file was degenerate**
(undertrained/broken at export), not a preprocessing or label issue.

**Ruled out in sequence:**

| Test | Result | Conclusion |
|------|--------|------------|
| 4-known-inputs (potato healthy, tomato late blight, bell pepper healthy, potato early blight) | ALL output same class ~90% | Ruled out **label permutation** — permutation gives varying wrong answers |
| Original dataset image fed DIRECTLY (no print, no camera) | Still "Tomato Late blight" 84.8% | Ruled out **camera/preprocessing** |
| Verified float32 in/out (NOT quantized) | `[-1, 1]` preprocessing appropriate | Ruled out **quantization mismatch** |
| **Final conclusion** | Model file itself broken | **Retraining required** |

### Retraining — Stage 1: Colab CPU (Proof of Concept)

- Small custom CNN on 3200-image subset
- 73.8% val accuracy
- 4/5 sanity OK (model learns, underfits)

### Retraining — Stage 2: RTX 5050/WSL2 (Production Model)

**Environment:**
- WSL2 Ubuntu + TF 2.21 + pip CUDA 12.9
- GPU bring-up: `cudnn .so.9` symlinks + `LD_LIBRARY_PATH` for pip nvidia dirs
- `nvidia-smi`: driver 610, CUDA UMD 13.3

**Training config:**
```python
base_model = MobileNetV3Small(weights='imagenet', include_top=False)
# FULL dataset: 387 MB, 16 classes
epochs = 20
EarlyStopping(patience=4, restore_best_weights=True)
```

**Result:**
```
Validation accuracy: 95.1%
Sanity checks: 5/5 passed
  - tomato early blight
  - tomato target spot
  - tomato late blight
  - tomato bacterial spot
  - tomato septoria
```

**Label safety:** `class_names.json` exported from `train_ds.class_names` in
the **same script** → label misalignment structurally impossible.

### Deployment Loop

```bash
# On WSL2 (training machine)
scp plant_health.tflite class_names.json yvette_pi@[PI_IP]:~/ros2_ws/src/robot_control/models/

# On Pi
mv models/plant_health.tflite models/plant_health.tflite.bak
mv models/class_names.json models/class_names.json.bak
mv models/plant_health.tflite.new models/plant_health.tflite
mv models/class_names.json.new models/class_names.json
sudo reboot

# After reboot
ros2 launch robot_control bringup.launch.py
```

### Viva Terminology

| Question | Answer |
|----------|--------|
| "Is this object detection?" | No — **single-label image classifier**. Output: `[1, 16]` softmax. |
| "Why not YOLO?" | Station-based inspection isolates the leaf; classifier sufficient. YOLOv8n + edge accelerator is **Stage-2 future work**. |
| "Demo workflow?" | Waypoint positions leaf → classify → log to dashboard. |

### Report Framing

Station-based inspection = **deliberate design:**
- Stable framing supports classifier accuracy
- Pi 5 compute favors short high-quality inferences
- Farmer value chain: patrol row → inspect at stations → log positions

Optional stretch: "patrol mode" (1 Hz classify while creeping 0.15 m/s) —
~30 lines using existing components.

### Quick Fixes Recorded

| Issue | Fix |
|-------|-----|
| TF + pip CUDA WSL2: "Cannot dlopen some GPU libraries" | cudnn symlink fix → then add all `nvidia/*/lib` dirs to `LD_LIBRARY_PATH` |
| file.io links expire if opened in browser before `wget` | Verify with `file` command; HTML error page saved as `.jpg` |
| `scp` on Windows with placeholders | Use real paths or Tab completion; spaces need quotes |

### Next Steps

1. Deploy new model to Pi (scp + backup + reboot)
2. 8-print score test (expect 7–8/8)
3. Straight run + box test with new EKF + min_pwm 0.25

---

*Yvette Lee EnQi (25034155) — Graduation Project, 2026*
