# Project Status

**Yvette Lee EnQi (25034155)** — Autonomous Agricultural Robot for Crop Health Monitoring
Last updated: 22 October 2026 · Viva: 2 December 2026

---

## Repo Structure

```
robot_control/
├── robot_control/
│   ├── motor_driver.py          # PWM differential drive + emergency cut-off
│   ├── camera_stream.py         # Flask MJPEG stream (port 5000)
│   ├── capture.py               # Single photo capture
│   ├── ai_inference.py          # TFLite inference, publishes /plant_health
│   ├── encoder_node.py          # 4-wheel encoders + odometry + TF
│   ├── imu_node.py              # BNO055 I2C IMU, publishes /imu/data
│   ├── gps_node.py              # NEO-8M UART GPS, publishes /fix
│   ├── env_node.py              # AHT30 I2C temp/humidity, publishes /env/*
│   ├── waypoint_follower.py     # Indoor autonomous nav, pause-resume on emergency
│   └── ultrasonic_node.py       # 2× HC-SR04 front sensors, debounced emergency stop
├── launch/
│   └── bringup.launch.py        # 9-process one-command bringup
├── config/
│   └── ekf.yaml                 # robot_localization EKF config
├── dashboard/                   # Mission Control (Flask, port 8080)
│   ├── app.py                   # Server + camera proxy
│   ├── result_logger.py
│   ├── data/results.json
│   ├── templates/index.html     # Mission Control page
│   └── drive/control.html       # Standalone drive page
├── models/                      # plant_health.tflite + class_names.json
├── training/                    # PlantVillage training pipeline scripts
└── docs/                        # Build log, status, command reference, figures
```

## What Works Now

1. SSH access from Windows PowerShell; workspace builds with colcon
2. Camera live stream (port 5000) and photo capture via ROS2 node
3. **AI inference on-device** — 16-class MobileNetV3-Small, TFLite float16,
   90.1% val accuracy, 3.5 ms/frame (282 FPS) on Pi 5 CPU; /plant_health
   topic verified end-to-end with confidence threshold (0.60 → unknown_no_plant)
4. **Mission Control dashboard** (port 8080) — unified page with live sensor
   cards (GPS, odom, heading, env, AI scan), embedded camera + drive pad,
   keyboard WASD/arrow control, waypoint Save/Run/Stop buttons, GPS map,
   results table. All data via rosbridge WebSocket. Camera proxy with zero
   hardcoded IPs.
5. **4-wheel drive teleop** — dual L298N via breadboard signal sharing;
   forward and turn-in-place verified with keyboard teleop and web drive pad
6. **One-command bringup** — `ros2 launch robot_control bringup.launch.py`
   starts 9 processes: motor, encoder, IMU, env, GPS, EKF, waypoint follower,
   ultrasonic, rosbridge, and camera stream
7. **Web drive control** — embedded in Mission Control + standalone at
   `/control` (WASD/arrow keys, speed slider, auto-stop, no hardcoded IP)
8. **Encoder odometry** — 4× LM393 encoders wired (GPIO 5/6/13/19), publishes
   /wheel_ticks + /odom + odom→base_link TF; calibrated ~90 ticks/m,
   ±10% per-leg accuracy, zero drift at rest
9. **BNO055 IMU** — I2C @0x29, NDOF mode, publishes /imu/data at 20 Hz
   (quaternion + gyro + accel). Onboard fusion; no Madgwick needed.
10. **NEO-8M GPS** — UART /dev/ttyAMA0 @9600, publishes /fix at 1 Hz
    always (status -1 when no fix). Stream verified; position fix needs sky view.
11. **AHT30 environmental sensor** — I2C (shares bus with BNO055), publishes
    /env/temperature and /env/humidity
12. **robot_localization EKF** — fuses /odom + /imu/data → /odometry/filtered
    at 20 Hz (two_d_mode, world_frame: odom). Encoder covariances added.
13. **Indoor waypoint navigation** — waypoint_follower node: Save waypoints
    from EKF pose, Run to autonomously navigate with proportional control
    (turn-in-place threshold 0.5 rad, 15 cm tolerance). Manual drive resumes
    after Stop via autonomous flag.
14. **Ultrasonic emergency stop v2** — 2× HC-SR04 front sensors (Trig GPIO17/23,
    Echo GPIO22/27 with voltage dividers). Motor-level cut-off: motor_driver
    zeroes both motors on `/emergency_stop`. Waypoint follower pause-resume:
    freezes on obstacle, auto-resumes when clear. Noise filtering: staggered
    pings (+20ms), median-of-3 sampling, 5-reading debounce, 2cm glitch filter.
    Threshold: 10cm (indoor), configurable via `THRESHOLD_CM`.

## What Is Left (Priority Order)

| # | Task | Due |
|---|------|-----|
| 1 | AI scan at each waypoint (auto capture → classify → log) | Nov |
| 2 | Field-test waypoint accuracy on actual floor | Nov |
| 3 | ADS1115 battery monitor (when LiPo returns) | Nov |
| 4 | Report writing + documentation | Nov–Dec |
| 5 | Viva presentation slides | 30 Nov |
| 6 | Final demo / viva | **2 Dec 2026** |

## Hardware Status

| Component | Status | Notes |
|-----------|--------|-------|
| Raspberry Pi 5 + Ubuntu 24.04 | Working | ROS2 Jazzy, 8 GB RAM |
| USB Webcam (1080p) | Working | V4L2/UVC, replaces Pi Camera v2 |
| Dual L298N + 4× TT motors | Working | Breadboard signal sharing |
| 4× LM393 encoders | Working | GPIO 5/6/13/19, ~90 ticks/m |
| BNO055 IMU | Working | I2C @0x29, NDOF mode, onboard fusion |
| NEO-8M GPS | Working | UART /dev/ttyAMA0, 1 Hz, needs sky view |
| AHT30 temp/humidity | Working | Shares I2C bus with BNO055 |
| 2× HC-SR04 ultrasonic | Working | Trig 17/23, Echo 22/27, 10cm threshold |
| 3S LiPo 11.1V 5500mAh | Borrowed | ~3.5 h runtime; return by 4 Dec |
| HW-688 buck converter | Working | 12V→5V logic power |
| ADS1115 battery monitor | Pending | When LiPo returns |
| Front bumper / protective guard | Not built | Optional for outdoor demo |

## GPIO Pinout (BCM, Final)

| GPIO | Function | Pin # |
|------|----------|-------|
| 12 | ENA (PWM, left motors) | 32 |
| 16 | IN1 (left forward) | 36 |
| 20 | IN2 (left reverse) | 38 |
| 18 | ENB (PWM, right motors) | 12 |
| 25 | IN3 (right forward) | 22 |
| 26 | IN4 (right reverse) | 37 |
| 5 | Encoder FL (D0) | 29 |
| 6 | Encoder FR (D0) | 31 |
| 13 | Encoder RL (D0) | 33 |
| 19 | Encoder RR (D0) | 35 |
| 2 | SDA (I2C) | 3 |
| 3 | SCL (I2C) | 5 |
| 14 | UART TX | 8 |
| 15 | UART RX | 10 |
| 17 | HC-SR04 Trig #1 | 11 |
| 23 | HC-SR04 Trig #2 | 16 |
| 22 | HC-SR04 Echo #1 (with divider) | 15 |
| 27 | HC-SR04 Echo #2 (with divider) | 13 |

**Spare GPIO:** 4, 7, 8, 9, 10, 11, 21, 24

## Topic Map

| Topic | Type | Publisher | Subscriber(s) |
|-------|------|-----------|---------------|
| /cmd_vel | Twist | dashboard, waypoint_follower, teleop | motor_driver |
| /wheel_ticks | Int32MultiArray | encoder_node | — |
| /odom | Odometry | encoder_node | ekf_filter_node |
| /imu/data | Imu | imu_node | ekf_filter_node |
| /odometry/filtered | Odometry | ekf_filter_node | waypoint_follower |
| /fix | NavSatFix | gps_node | dashboard, navsat_transform_node |
| /env/temperature | Temperature | env_node | dashboard |
| /env/humidity | RelativeHumidity | env_node | dashboard |
| /plant_health | String (JSON) | ai_inference | dashboard |
| /ultrasonic/front | Float32 | ultrasonic_node | — |
| /emergency_stop | Bool | ultrasonic_node | motor_driver, waypoint_follower |
| /waypoint/save | Empty | dashboard | waypoint_follower |
| /waypoint/clear | Empty | dashboard | waypoint_follower |
| /waypoint/run | Empty | dashboard | waypoint_follower |
| /waypoint/stop | Empty | dashboard | waypoint_follower |

## Known Issues

1. **Jittery manual drive** — robot stutters during web drive. Suspected
   vibration-induced false ultrasonic readings (median+debounce applied,
   needs retest), or `min_pwm=0.25` lurch on resume. Next: retest with
   echo running during drive; if persists, add acceleration ramp.
2. **Encoder drift** — ±10% per-leg without GPS loop closure. Documented
   limitation; EKF helps but does not eliminate accumulated drift.
3. **IMU tilt** — BNO055 mounted ~18° off horizontal. Must remount flat
   before outdoor nav2 demo.
4. **GPS no fix indoors** — expected; status -1 with 0.0/0.0. Needs sky
   view for position lock. Navsat transform node ready for outdoor use.
5. **LCD moiré** — leaf images on phone screens misclassify occasionally.
   Use printed photos or real leaves for demo.

## Critical Path

```
[COMPLETED] Chassis → AI pipeline → Electronics → 4WD → Web drive
[COMPLETED] Bringup launch → Encoders → Sensors → Dashboard
[COMPLETED] EKF → Waypoint nav → Ultrasonic v1 → Ultrasonic v2
[ACTIVE]    AI scan at waypoint → Field test → Battery monitor
[UPCOMING]  Report → Slides → Viva (2 Dec 2026)
```

## Quick Commands

```bash
# Build workspace
cd ~/ros2_ws && colcon build --symlink-install && source install/setup.bash

# One-command bringup (9 processes)
ros2 launch robot_control bringup.launch.py

# Dashboard (second terminal)
python3 ~/ros2_ws/src/robot_control/dashboard/app.py

# Monitor emergency stop
ros2 topic echo /emergency_stop

# Monitor ultrasonic distance
ros2 topic echo /ultrasonic/front

# Verify all nodes running
ros2 node list
```

## File Locations

| File | Path |
|------|------|
| Workspace | `~/ros2_ws/` |
| Package source | `~/ros2_ws/src/robot_control/` |
| Bringup launch | `~/ros2_ws/src/robot_control/launch/bringup.launch.py` |
| EKF config | `~/ros2_ws/src/robot_control/config/ekf.yaml` |
| Motor driver | `~/ros2_ws/src/robot_control/robot_control/motor_driver.py` |
| Encoder node | `~/ros2_ws/src/robot_control/robot_control/encoder_node.py` |
| IMU node | `~/ros2_ws/src/robot_control/robot_control/imu_node.py` |
| GPS node | `~/ros2_ws/src/robot_control/robot_control/gps_node.py` |
| Env node | `~/ros2_ws/src/robot_control/robot_control/env_node.py` |
| Waypoint follower | `~/ros2_ws/src/robot_control/robot_control/waypoint_follower.py` |
| Ultrasonic node | `~/ros2_ws/src/robot_control/robot_control/ultrasonic_node.py` |
| Camera stream | `~/ros2_ws/src/robot_control/robot_control/camera_stream.py` |
| Dashboard app | `~/ros2_ws/src/robot_control/dashboard/app.py` |
| Dashboard HTML | `~/ros2_ws/src/robot_control/dashboard/templates/index.html` |
| Drive page | `~/ros2_ws/src/robot_control/dashboard/drive/control.html` |
| AI model | `~/ros2_ws/src/robot_control/models/plant_health.tflite` |
| Waypoint JSON | `~/ros2_ws/src/robot_control/waypoints.json` |
| Results log | `~/ros2_ws/src/robot_control/dashboard/data/results.json` |
| Build log | `docs/BUILD_LOG.md` |
| Command reference | `docs/COMMAND_REFERENCE.md` |

---

*Yvette Lee EnQi (25034155) — Graduation Project, 2026*
