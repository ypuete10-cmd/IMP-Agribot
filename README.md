# IMP-AgriBot

**Autonomous agricultural robot for crop health monitoring.**
A Raspberry Pi 5–powered rover that navigates to GPS waypoints, captures plant
images, and classifies crop health on-device using a TFLite model — with
real-time sensor data, teleop drive control, indoor autonomous waypoint
navigation with emergency stop hardening, **AI scan at each waypoint**
(event-driven scanner + scan handshake), and results displayed on a unified
farmer-facing Mission Control dashboard.


![AgriBot system](https://github.com/user-attachments/assets/dc5bf120-d234-43b8-aae1-257221774d6b)

---

## Hardware

| Component | Purpose |
|-----------|---------|
| Raspberry Pi 5 (Ubuntu 24.04, ROS2 Jazzy) | Main computer |
| USB Webcam (1080p, V4L2) | Plant imaging |
| MobileNetV3-Small (TFLite float16) | On-device disease classification (16 classes) |
| BNO055 IMU (I2C, onboard fusion) | Orientation + gyro + accel for EKF |
| NEO-8M GNSS (UART) | GPS waypoints + position fix |
| 4× LM393 wheel encoders (GPIO) | Odometry + distance tracking |
| AHT30 (I2C) | Temperature + humidity |
| 4× TT motors + dual L298N drivers | 4-wheel differential drive |
| 2× HC-SR04 ultrasonic sensors | Front emergency stop (<10 cm) |
| 3S LiPo 11.1V 5500mAh | Power (~3.5 h runtime) |

> **Note:** The Pi Camera Module v2 was retired — Ubuntu 24.04 lacks the
> `rpicam` ISP stack. USB webcam (V4L2/UVC) is plug-and-play.
>
> The shop substituted BNO055 for the originally ordered MPU9250. Kept
> deliberately: onboard fusion processor outputs ready quaternion (no
> Madgwick/Mahony library needed).

---

## Software Architecture

- **ROS2 package `robot_control`** — 10 live processes:
  - `camera_stream` — Flask MJPEG stream (port 5000) + writes every frame to `/tmp/latest_frame.jpg`
  - `motor_driver` — PWM differential drive + emergency cut-off + watchdog latch fix, subscribes `/cmd_vel`
  - `encoder_node` — 4-wheel counting + signed odometry + TF
  - `imu_node` — BNO055 I2C fusion, publishes `/imu/data` at 20 Hz
  - `gps_node` — NEO-8M UART parser, publishes `/fix` at 1 Hz
  - `env_node` — AHT30 temp/humidity, publishes `/env/*`
  - `ekf_node` — `robot_localization`, fuses `/odom` + `/imu/data` → `/odometry/filtered` (5 Hz)
  - `waypoint_follower` — indoor autonomous nav, pause-resume on emergency + scan handshake
  - `ultrasonic_node` — 2× HC-SR04 front sensors, debounced emergency stop
  - `ai_inference` — **event-driven TFLite scanner**: triggers on `/waypoint/reached`, classifies shared frame, publishes `/plant_health` + `/waypoint/scan_done`

- **AI pipeline** — PlantVillage → 16-class subset (15 diseases + Other) →
  MobileNetV3-Small transfer learning → TFLite float16 (~90.1% val accuracy)

- **Mission Control dashboard** (Flask, port 8080) — unified page with live
  sensor cards (GPS, odom, heading, environment, AI scan), embedded camera +
  drive pad, **keyboard WASD/arrow control**, **waypoint Save/Run/Stop buttons**,
  GPS health map, results table. All sensor data via `roslib.js` over rosbridge
  WebSocket. Camera proxy with zero hardcoded IPs. Throttle rates on heavy
  topics to prevent rosbridge queue overflow.

- **Web drive control** — browser teleop at `/control` (standalone) and
  embedded in Mission Control. WASD + speed slider + auto-stop.

- **Emergency stop v2** — motor-level cut-off in `motor_driver.py` (zeroes
  motors for ALL cmd_vel sources). Waypoint follower pause-resume: freezes
  on obstacle, auto-resumes when clear. Ultrasonic noise filtering:
  staggered pings, median-of-3, 5-reading debounce, 2cm glitch filter.

- **AI-waypoint integration** — event-driven scan handshake: follower publishes
  `/waypoint/reached` → AI classifies → publishes `/waypoint/scan_done` →
  follower auto-resumes to next waypoint. Frame sharing via `/tmp/latest_frame.jpg`
  avoids camera device contention.

- **One-command bringup** — `ros2 launch robot_control bringup.launch.py`
  starts the full robot stack (10 processes: 9 ROS nodes + camera stream).

---

## Results

**Working autonomous navigation + AI scan** — end-to-end mission verified:
Run → Drive → Arrive → Scan → Resume → Complete. ~5 cm accuracy over 1 m.
(29 Oct 2026):

![Working autonomous navigation — Mission Control dashboard during autonomous run with live sensor cards, camera feed, and waypoint status](https://github.com/user-attachments/assets/525101c1-b360-4ae8-b857-4fdcf9e1f634)

**Emergency stop v2** — motor-level cut-off with pause-resume waypoint
navigation (22 Oct 2026):

![Emergency stop v2 — front HC-SR04 ultrasonic sensors with voltage dividers](https://github.com/user-attachments/assets/79f3b59e-ecee-4f50-99c0-70cf029cba2b)

**Mission Control dashboard** — live sensor strip, camera, drive pad, GPS map,
and results table (9 Oct 2026):

![Mission Control dashboard — sensor cards, camera feed, drive pad](https://github.com/user-attachments/assets/669aabed-7c8f-424b-a11e-766d7152212e)

**Live end-to-end inference test** — robot camera classifying a leaf displayed
on phone (30 Sep 2026):

![Live inference test — robot classifying leaf image on phone](https://github.com/user-attachments/assets/b16aba8d-723a-4b9d-9569-3d3ec4cedd94)

**TFLite performance** on Pi 5 CPU — no accelerator needed:

![TFLite benchmark: 3.5 ms/frame, 282 FPS](https://github.com/user-attachments/assets/e3fa8fbb-48d4-4445-a93a-bd0293608a8d)

---

## Documentation

| File | Contents |
|------|----------|
| **[Build Log](docs/BUILD_LOG.md)** | Dated progress history with photos |
| **[Project Status](docs/STATUS.md)** | Current progress, GPIO pinout, critical path |
| **[Command Reference](docs/COMMAND_REFERENCE.md)** | All commands, quick fixes, file locations |

---

## Repository Structure

```
robot_control/
├── robot_control/              # ROS2 nodes
│   ├── camera_stream.py         # + frame sharing to /tmp/latest_frame.jpg
│   ├── capture.py
│   ├── ai_inference.py          # + event-driven waypoint scanner
│   ├── motor_driver.py          # + emergency cut-off + watchdog latch
│   ├── encoder_node.py
│   ├── imu_node.py
│   ├── gps_node.py
│   ├── env_node.py
│   ├── waypoint_follower.py     # + scan handshake
│   └── ultrasonic_node.py       # + noise filtering
├── launch/
│   └── bringup.launch.py        # 10-process bringup
├── config/
│   └── ekf.yaml                 # robot_localization EKF config (5 Hz)
├── dashboard/                    # Mission Control (Flask)
│   ├── app.py                    # Server + camera proxy
│   ├── result_logger.py
│   ├── data/results.json
│   ├── templates/index.html      # Mission Control page
│   └── drive/control.html        # Standalone drive page
├── models/                       # plant_health.tflite + class_names.json
├── training/                     # PlantVillage training pipeline scripts
└── docs/                         # Build log, status, command reference, figures
```

---

## Quick Start

```bash
# 1. SSH into the Pi
ssh yvette_pi@[PI_IP]

# 2. Start the robot stack (10 processes: 9 ROS nodes + camera stream)
cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash
ros2 launch robot_control bringup.launch.py

# 3. In a second terminal, start the dashboard
python3 ~/ros2_ws/src/robot_control/dashboard/app.py

# 4. Open in browser
# Mission Control:  http://[PI_IP]:8080
# Camera only:      http://[PI_IP]:5000
# Drive page:       http://[PI_IP]:5000/control
```

---

## Key Specs

| Metric | Value |
|--------|-------|
| AI model | MobileNetV3-Small, 16 classes |
| Validation accuracy | 90.1% |
| Inference speed | 3.5 ms/frame (282 FPS) |
| Platform | Raspberry Pi 5, Ubuntu 24.04 |
| ROS2 distro | Jazzy Jalisco |
| Runtime | ai-edge-litert + NumPy 1.26.4 |
| IMU publish rate | 20 Hz (NDOF mode, onboard fusion) |
| GPS publish rate | 1 Hz (always publishing, even indoors) |
| Encoder odometry | 10 Hz, ~90 ticks/m, ±10% per-leg |
| EKF output | 5 Hz, fuses encoders + IMU (two_d_mode) |
| Waypoint navigation | Proportional control, 15 cm tolerance, 0.15 rad orientation |
| Forward speed | 0.3 m/s max (was 0.15) |
| Turn-in-place threshold | 0.8 rad (was 0.5) |
| Emergency stop | Motor-level cut-off, 10 cm threshold, pause-resume |
| Ultrasonic filtering | Staggered pings, median-of-3, 5-reading debounce, 2cm glitch filter |
| AI trigger | Event-driven on `/waypoint/reached` |
| Scan handshake | `/waypoint/reached` → classify → `/waypoint/scan_done` → resume |
| Frame sharing | `/tmp/latest_frame.jpg` (avoids camera contention) |
| Results log | Atomic JSON write to `dashboard/data/results.json` |
| Dashboard | Flask + roslib.js + Leaflet + OpenStreetMap |
| Web drive | rosbridge WebSocket, /cmd_vel at 10 Hz |
| QoS | Explicit RELIABLE + VOLATILE + KEEP_LAST/10 on /cmd_vel |
| Watchdog | Latch fix — stops once on timeout, resets on new cmd_vel |
| Navigation accuracy | ~5 cm over 1 m distance |

---

## Project Timeline

| Milestone | Date |
|-----------|------|
| Chassis printed + assembled | 28 Sep 2026 |
| AI pipeline working | 22 Sep 2026 |
| Electronics + live inference | 30 Sep 2026 |
| Model retrained (domain-gap fix) | 1 Oct 2026 |
| 4-wheel drive verified | 3 Oct 2026 |
| Web drive + bringup launch | 6 Oct 2026 |
| Encoder odometry complete | 7 Oct 2026 |
| Sensor stack complete (IMU + GPS) | 8 Oct 2026 |
| Mission Control dashboard live | 9 Oct 2026 |
| EKF + indoor waypoint navigation | 12 Oct 2026 |
| Ultrasonic emergency stop | 14 Oct 2026 |
| Emergency stop hardening v2 | 22 Oct 2026 |
| AI-waypoint integration | 28 Oct 2026 |
| **Working autonomous nav + AI scan** | **29 Oct 2026** |
| Multi-waypoint mission with plant photos | *Next* |
| Camera lag reduction | *Next* |
| Field-test waypoint accuracy | *Next* |
| ADS1115 battery monitor | *Next* |
| **Report due** | 25 Nov 2026 |
| **Slides due** | 30 Nov 2026 |
| **Viva** | 2 Dec 2026 |

---

*Yvette Lee EnQi (25034155) — Graduation Project, 2026*
