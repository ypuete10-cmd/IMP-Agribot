# IMP-AgriBot

**Autonomous agricultural robot for crop health monitoring.**
A Raspberry Pi 5–powered rover that navigates to GPS waypoints, captures plant
images, and classifies crop health on-device using a TFLite model — with
real-time sensor data, teleop drive control, indoor autonomous waypoint
navigation with ultrasonic emergency stop, and results displayed on a unified
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
| 2× HC-SR04 ultrasonic (GPIO) | Front obstacle detection + emergency stop |
| AHT30 (I2C) | Temperature + humidity |
| 4× TT motors + dual L298N drivers | 4-wheel differential drive |
| 3S LiPo 11.1V 5500mAh | Power (~3.5 h runtime) |

&gt; **Note:** The Pi Camera Module v2 was retired — Ubuntu 24.04 lacks the
&gt; `rpicam` ISP stack. USB webcam (V4L2/UVC) is plug-and-play.
&gt;
&gt; The shop substituted BNO055 for the originally ordered MPU9250. Kept
&gt; deliberately: onboard fusion processor outputs ready quaternion (no
&gt; Madgwick/Mahony library needed).

---

## Software Architecture

- **ROS2 package `robot_control`** — 9 live nodes:
  - `camera_stream` — Flask MJPEG stream (port 5000)
  - `motor_driver` — PWM differential drive, subscribes `/cmd_vel`
  - `encoder_node` — 4-wheel counting + signed odometry + TF
  - `imu_node` — BNO055 I2C fusion, publishes `/imu/data` at 20 Hz
  - `gps_node` — NEO-8M UART parser, publishes `/fix` at 1 Hz
  - `env_node` — AHT30 temp/humidity, publishes `/env/*`
  - `ekf_filter_node` — robot_localization, fuses `/odom` + `/imu/data` → `/odometry/filtered`
  - `waypoint_follower` — indoor autonomous navigation with emergency-stop handling
  - `ultrasonic_node` — 2× HC-SR04 front sensors, publishes `/ultrasonic/front` + `/emergency_stop`
  - `ai_inference` — TFLite classification, publishes `/plant_health`

- **Safety chain:** `ultrasonic_node` publishes `/emergency_stop` (True when
  obstacle &lt;30 cm) → `waypoint_follower` halts autonomous run and zeroes
  `/cmd_vel`, logging "EMERGENCY STOP — obstacle detected!"

- **AI pipeline** — PlantVillage → 16-class subset (15 diseases + Other) →
  MobileNetV3-Small transfer learning → TFLite float16 (~90.1% val accuracy)

- **Mission Control dashboard** (Flask, port 8080) — unified page with live
  sensor cards (GPS, odom, heading, environment, AI scan, ultrasonic distance,
  E-stop status), embedded camera + drive pad, GPS health map, results table.
  All sensor data via `roslib.js` over rosbridge WebSocket. Camera proxy with
  zero hardcoded IPs. Keyboard WASD/arrows + waypoint Save/Run/Stop buttons.

- **One-command bringup** — `ros2 launch robot_control bringup.launch.py`
  starts the full robot stack (9 ROS nodes + rosbridge + camera stream),
  with `navsat_transform_node` in the launch file on standby for outdoor GPS use.

---

## Results

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
├── robot_control/        # ROS2 nodes
│   ├── camera_stream.py
│   ├── capture.py
│   ├── ai_inference.py
│   ├── motor_driver.py
│   ├── encoder_node.py
│   ├── imu_node.py
│   ├── gps_node.py
│   ├── env_node.py
│   ├── waypoint_follower.py
│   └── ultrasonic_node.py
├── launch/
│   └── bringup.launch.py     # One-command robot stack bringup
├── config/
│   └── ekf.yaml              # robot_localization EKF config
├── dashboard/                  # Mission Control (Flask)
│   ├── app.py                  # Server + camera proxy
│   ├── result_logger.py
│   ├── data/results.json
│   ├── templates/index.html    # Mission Control page
│   └── drive/control.html      # Standalone drive page
├── models/                     # plant_health.tflite + class_names.json
├── training/                   # PlantVillage training pipeline scripts
└── docs/                       # Build log, status, command reference, figures
```

---

## Quick Start

```bash
# 1. SSH into the Pi
ssh yvette_pi@[PI_IP]

# 2. Start the robot stack (9 nodes + rosbridge + camera)
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
| EKF output | /odometry/filtered at 20 Hz |
| Emergency stop | 2× HC-SR04, triggers &lt;30 cm |
| Dashboard | Flask + roslib.js + Leaflet + OpenStreetMap |
| Web drive | rosbridge WebSocket, /cmd_vel at 10 Hz |

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
| **Ultrasonic emergency stop** | **14 Oct 2026** |
| **AI scan at each waypoint** | *Next* |
| **Field-test waypoint accuracy** | *Next* |
| **Report due** | 25 Nov 2026 |
| **Slides due** | 30 Nov 2026 |
| **Viva** | 2 Dec 2026 |

---

*Yvette Lee EnQi (25034155) — Integrated Design Project, 2026*
