# Project Status

**Yvette Lee EnQi (25034155)** — Autonomous Agricultural Robot for Crop Health Monitoring
Last updated: 7 October 2026 · Viva: 2 December 2026

---

## Repo Structure

```
robot_control/
├── robot_control/
│   ├── motor_driver.py      # subscribes /cmd_vel, PWM + dir control
│   ├── camera_stream.py     # Flask MJPEG stream (port 5000)
│   ├── capture.py           # single photo capture
│   ├── ai_inference.py      # TFLite inference, publishes /plant_health
│   ├── encoder_node.py      # 4-wheel encoder counting + odometry + TF
│   └── camera_publisher.py  # /camera/image_raw (integration pending)
├── dashboard/               # Flask farmer dashboard (port 8080)
├── models/                  # plant_health.tflite, class_names.json
├── training/                # PlantVillage training pipeline scripts
└── docs/                    # build log, command reference, figures
```

## What Works Now

1. SSH access from Windows PowerShell; workspace builds with colcon
2. Camera live stream (port 5000) and photo capture via ROS2 node
3. **AI inference on-device** — 16-class MobileNetV3-Small, TFLite float16,
   90.1% val accuracy, 3.5 ms/frame (282 FPS) on Pi 5 CPU; /plant_health
   topic verified end-to-end with confidence threshold (0.60 → unknown_no_plant)
4. **Farmer dashboard** — results table + GPS health map (simulated scans;
   real GPS+AI hookup pending)
5. **4-wheel drive teleop** — dual L298N via breadboard signal sharing;
   forward and turn-in-place verified with teleop_twist_keyboard and web control
6. **One-command bringup** — `ros2 launch robot_control bringup.launch.py`
   starts motor driver, rosbridge, camera stream, and dashboard together
7. **Web drive control** — browser-based teleop at `/control` with WASD,
   speed slider, auto-stop, no hardcoded IP
8. **Encoder odometry** — 4× LM393 encoders wired (GPIO 5/6/13/19), publishes
   /wheel_ticks + /odom + odom→base_link TF; calibrated 90 ticks/m,
   ±10% per-leg accuracy, zero drift at rest

## Hardware Status

| Item | Status |
|------|--------|
| Pi 5 (Ubuntu 24.04, ROS2 Jazzy) | ✅ Running |
| USB webcam (/dev/video0) | ✅ Working (Pi Cam v2 retired — Ubuntu 24.04 incompatible) |
| Dual L298N motor drivers | ✅ Wired, 4-wheel drive working (breadboard signal sharing) |
| Breadboard (signal + power rails) | ✅ 6 GPIO → both boards; 5V/GND/12V distributed |
| 4× LM393 wheel encoders | ✅ Wired (GPIO 5/6/13/19), 3.3V, pull-up; odometry publishing |
| ros-jazzy-rosbridge-suite | ✅ Installed |
| 3S LiPo 5500mAh | Purchased; running on 12V wall adapter until charger/safe bag arrive |
| NEO-8M GPS | Purchased, not wired (UART) |
| MPU9250 IMU | Purchased, not wired (I2C) |
| AHT20 + BMP280 | Purchased, not wired (I2C) |
| 2× HC-SR04 ultrasonic | From lab, not wired |

## Critical Path (remaining ~7.5 weeks)

1. ~~Wire L298N #2 → full 4-wheel drive teleop~~ ✅ DONE 03/10
2. ~~One-command bringup + web drive dashboard~~ ✅ DONE 06/10
3. ~~Encoder odometry (4-wheel, signed counts, TF)~~ ✅ DONE 07/10
4. Wire GPS (NEO-8M) to UART, enable_uart=1, test /fix topic
5. Wire IMU + env sensors (I2C) → verify i2cdetect 0x68/0x38/0x76
6. robot_localization EKF (fuse encoders + IMU + GPS)
7. nav2 waypoint navigation
8. Dashboard: replace simulated scans with real GPS + /plant_health
9. Report writing + demo prep

## GPIO Pinout

| GPIO | Pin | Function | Status |
|------|-----|----------|--------|
| 12 | 32 | ENA both boards (PWM, left speed) | ✅ Wired |
| 16 | 36 | IN1 both boards (left dir) | ✅ Wired |
| 20 | 38 | IN2 both boards (left dir) | ✅ Wired |
| 18 | 12 | ENB both boards (PWM, right speed) | ✅ Wired |
| 25 | 22 | IN3 both boards (right dir) | ✅ Wired |
| 26 | 37 | IN4 both boards (right dir) | ✅ Wired |
| 5 | 29 | Encoder FL (D0, 3.3V) | ✅ Wired |
| 6 | 31 | Encoder RL (D0, 3.3V) | ✅ Wired |
| 13 | 33 | Encoder FR (D0, 3.3V) | ✅ Wired |
| 19 | 35 | Encoder RR (D0, 3.3V) | ✅ Wired |
| 2/3 | 3/5 | I2C (IMU, AHT20, BMP280) | ⬜ Not wired |
| 14/15 | 8/10 | UART (GPS) | ⬜ Not wired |

**GPIO budget:** 14 used, 12 spare (4/7/8/9/10/11/17/21/22/23/24/27)

## Known Issues / Fixes Applied

- Pi Camera v2 incompatible with Ubuntu 24.04 → USB webcam (V4L2)
- GPIO busy error → kill old process before restart (motor, encoder)
- Motors need ≥25% PWM to overcome static friction → threshold coded in node
- ENA/ENB miswired during bring-up → rewired to align with IN pins
- Front wheels spun backwards → swapped motor lead polarity
- Front/back turning inversion → breadboard second output wire per GPIO row
- Count-only encoders cannot sense direction → fused from /cmd_vel
- Zero-cmd direction flip caused coasting miscounts → deadband patch (|cmd| &gt; 0.01)
- tflite-runtime has no Python 3.12 wheels → ai-edge-litert; NumPy pinned to 1.26.4
- Camera device number changes after reboot → re-verify /dev/videoN before use
- WSL cannot SSH to Pi on hotspot → use Windows PowerShell

## Notes for Report

- Chassis is open-source adapted (Thingiverse), not designed from scratch —
  **must cite original source** in references
- Custom work: Pi mounting tray, camera mast, two-deck layout, wiring integration,
  breadboard signal-sharing architecture (dual L298N per-channel), encoder
  odometry with cmd_vel direction fusion, deadband patch for coasting drift
- "Future improvements" section: deferred sensors (rain, soil, air quality),
  solar panel, IP54 enclosure
- PlantVillage dataset © original authors (CC BY-SA) — attribute in report
- Known demo caveat: phone-screen leaf images may misclassify (LCD moiré) —
  use printed photos or real leaves for the viva demo
- Encoder limitation: ±10% per-leg distance accuracy; GPS fusion in nav2
  will correct drift globally
