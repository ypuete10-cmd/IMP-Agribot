# Pi 5 Command Reference — AgriBot

Yvette Lee EnQi (25034155) · Last updated: 22 October 2026

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
# Single capture + classify
ros2 run robot_control capture

# Continuous inference node
ros2 run robot_control ai_inference

# Verify topic
ros2 topic echo /plant_health
```

---

## 8. One-Command Bringup

**Starts 9 processes:**
```bash
cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash
ros2 launch robot_control bringup.launch.py
```

Processes launched:
- `motor_driver` — PWM differential drive + emergency cut-off
- `encoder_node` — 4-wheel encoders + odometry + TF
- `imu_node` — BNO055 I2C IMU, 20 Hz
- `env_node` — AHT30 temp/humidity
- `gps_node` — NEO-8M UART GPS, 1 Hz
- `ekf_filter_node` — robot_localization EKF
- `navsat_transform_node` — GPS pipeline (standby for outdoor)
- `waypoint_follower` — indoor autonomous nav, pause-resume
- `ultrasonic_node` — 2× HC-SR04 emergency stop
- `rosbridge_server` — WebSocket bridge
- `camera_stream` — Flask MJPEG (port 5000)

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
- `min_pwm = 0.25`

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

---

## 12. Web Drive Control

**Embedded in dashboard + standalone at `/control`.**

- WASD / Arrow keys + speed slider
- Auto-stop on release / blur
- roslib.js → WebSocket → rosbridge → /cmd_vel at 10 Hz
- `autonomous` flag prevents dashboard zeros during waypoint Run

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

**Waypoint follower topics:**
```bash
ros2 topic pub /waypoint/save std_msgs/Empty {}
ros2 topic pub /waypoint/clear std_msgs/Empty {}
ros2 topic pub /waypoint/run std_msgs/Empty {}
ros2 topic pub /waypoint/stop std_msgs/Empty {}
```

**Parameters:**
- Turn-in-place threshold: `|yaw_err| &gt; 0.5 rad`
- Forward speed: `0.15 * dist` capped at `0.15 m/s`
- Angular cap: `±0.3 rad/s`
- Position tolerance: `15 cm`
- Orientation tolerance: `0.15 rad`

---

## 14. Ultrasonic Emergency Stop

**Topics:**
```bash
ros2 topic echo /ultrasonic/front    # Float32, minimum distance (m)
ros2 topic echo /emergency_stop      # Bool, True when &lt; threshold
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
| GPIO busy | `pkill -f &lt;node_name&gt;` before relaunch |
| `gpiochip_open(0)` fails on Pi 5 | Use `gpiochip_open(4)` |
| Waypoints "not saving" | Check `self.emergency` defined in `__init__` |
| Dashboard/waypoint cmd_vel conflict | `autonomous` flag in dashboard JS |

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
| Camera stream | `robot_control/camera_stream.py` |
| Dashboard app | `dashboard/app.py` |
| Dashboard HTML | `dashboard/templates/index.html` |
| Drive page | `dashboard/drive/control.html` |
| AI model | `models/plant_health.tflite` |
| Waypoint JSON | `waypoints.json` |
| Results log | `dashboard/data/results.json` |

---

## 17. Status Snapshot (22 Oct 2026)

| Component | Status |
|-----------|--------|
| Pi 5 + Ubuntu 24.04 + ROS2 Jazzy | Working |
| USB Webcam + V4L2 | Working |
| 4-wheel drive (dual L298N) | Working |
| 4× encoders + odometry | Working |
| BNO055 IMU (I2C, NDOF) | Working |
| NEO-8M GPS (UART) | Working (stream); fix needs sky view |
| AHT30 temp/humidity | Working |
| EKF (robot_localization) | Working |
| Indoor waypoint navigation | Working |
| Ultrasonic emergency stop v2 | Working (motor-level cut-off, pause-resume) |
| Mission Control dashboard | Working |
| Web drive control | Working |
| AI inference (TFLite) | Working |
| One-command bringup (9 processes) | Working |
| ADS1115 battery monitor | Pending |
| AI scan at waypoint | Pending |
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

1. **Jittery manual drive** — robot stutters during web drive.
   - Suspected: vibration-induced false ultrasonic readings (median+debounce
     applied, needs retest) OR `min_pwm=0.25` lurch on resume
   - Next: retest with echo running during drive; if persists, add
     acceleration ramp in motor driver

2. **Encoder drift** — ±10% per-leg without GPS loop closure

3. **IMU tilt** — BNO055 mounted ~18° off horizontal; remount before outdoor demo

4. **GPS no fix indoors** — expected; navsat transform ready for outdoor

5. **LCD moiré** — phone-screen leaves misclassify; use printed/real leaves

### Next Steps

| Priority | Task |
|----------|------|
| 1 | AI scan at each waypoint (auto capture → classify → log) |
| 2 | Field-test waypoint accuracy on actual floor |
| 3 | ADS1115 battery monitor (when LiPo returns) |
| 4 | Report writing + documentation |
| 5 | Slides (due 30 Nov) |
| 6 | Viva (2 Dec 2026) |

---

*Yvette Lee EnQi (25034155) — Graduation Project, 2026*
