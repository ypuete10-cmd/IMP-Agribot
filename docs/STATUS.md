# Project Status

**Yvette Lee EnQi (25034155)** — Autonomous Agricultural Robot for Crop Health Monitoring
Last updated: 9 October 2026 · Viva: 2 December 2026

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
│   ├── imu_node.py          # BNO055 I2C IMU, publishes /imu/data
│   ├── gps_node.py          # NEO-8M UART GPS, publishes /fix
│   ├── env_node.py          # AHT30 I2C temp/humidity, publishes /env/*
│   └── camera_publisher.py  # /camera/image_raw (integration pending)
├── dashboard/               # Flask Mission Control (port 8080)
│   ├── app.py               # server + camera proxy routes
│   ├── result_logger.py     # writes scans to data/results.json
│   ├── data/results.json    # shared data file
│   └── templates/index.html # Mission Control page
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
4. **Mission Control dashboard** (port 8080) — unified page with live sensor
   cards (GPS, odom, IMU heading, AHT30 env, AI scan), embedded camera +
   drive pad, GPS map, results table. All data via rosbridge WebSocket.
   Camera proxy routes with zero hardcoded IPs.
5. **4-wheel drive teleop** — dual L298N via breadboard signal sharing;
   forward and turn-in-place verified with keyboard teleop and web drive pad
6. **One-command bringup** — `ros2 launch robot_control bringup.launch.py`
   starts motor driver, encoder, IMU, env, GPS, rosbridge, and camera stream
7. **Web drive control** — embedded in Mission Control + standalone at
   `/control` (WASD, speed slider, auto-stop, no hardcoded IP)
8. **Encoder odometry** — 4× LM393 encoders wired (GPIO 5/6/13/19), publishes
   /wheel_ticks + /odom + odom→base_link TF; calibrated ~90 ticks/m,
   ±10% per-leg accuracy, zero drift at rest
9. **BNO055 IMU** — I2C @0x29, NDOF mode, publishes /imu/data at 20 Hz
   (quaternion + gyro + accel). Onboard fusion; no Madgwick needed.
10. **NEO-8M GPS** — UART /dev/ttyAMA0 @9600, publishes /fix at 1 Hz
    always (status -1 when no fix). Stream verified; position fix needs sky view.
11. **AHT30 environmental sensor** — I2C (shares bus with BNO055), publishes
    /env/temperature and /env/humidity

## Hardware Status

| Item | Status |
|------|--------|
| Pi 5 (Ubuntu 24.04, ROS2 Jazzy) | ✅ Running |
| USB webcam (/dev/video0) | ✅ Working (Pi Cam v2 retired) |
| Dual L298N motor drivers | ✅ Wired, 4-wheel drive working |
| Breadboard (signal + power rails) | ✅ 6 GPIO → both boards; 5V/GND/12V distributed |
| 4× LM393 wheel encoders | ✅ Wired (GPIO 5/6/13/19), 3.3V, odometry publishing |
| BNO055 IMU (I2C 0x29) | ✅ Live, /imu/data at 20 Hz, onboard fusion |
| NEO-8M GPS (UART /dev/ttyAMA0) | ✅ Publishing /fix; fix needs sky |
| AHT30 temp/humidity (I2C) | ✅ Live, /env/temperature + /env/humidity |
| ros-jazzy-rosbridge-suite | ✅ Installed |
| 3S LiPo 5500mAh | Purchased; running on 12V wall adapter until charger/safe bag arrive |
| BMP280 pressure (I2C) | Purchased, not wired (shares bus) |
| 2× HC-SR04 ultrasonic | From lab, not wired |
| MPU9250 (original order) | Shop substituted with BNO055 — kept deliberately |

## Critical Path (remaining ~7.5 weeks)

1. ~~Wire L298N #2 → full 4-wheel drive teleop~~ ✅ DONE 03/10
2. ~~One-command bringup + web drive dashboard~~ ✅ DONE 06/10
3. ~~Encoder odometry (4-wheel, signed counts, TF)~~ ✅ DONE 07/10
4. ~~IMU node (BNO055 I2C fusion)~~ ✅ DONE 08/10
5. ~~GPS node (NEO-8M UART /fix publisher)~~ ✅ DONE 08/10
6. ~~Mission Control dashboard (unified sensor + camera + drive)~~ ✅ DONE 09/10
7. robot_localization EKF (fuse /odom + /imu/data → /odometry/filtered)
8. nav2 waypoint navigation (GPS waypoints)
9. Report writing + demo prep

## GPIO / I2C / UART Map

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
| 2/3 | 3/5 | I2C (BNO055 @0x29, AHT30 share bus) | ✅ All live |
| 14/15 | 8/10 | UART /dev/ttyAMA0 (GPS) | ✅ GPS live |

**GPIO budget:** 16 used, 10 spare (4/7/8/9/10/11/17/21/22/23/24/27 minus 2 for I2C = 10)

## Known Issues / Fixes Applied

- Pi Camera v2 incompatible with Ubuntu 24.04 → USB webcam (V4L2)
- GPIO busy error → kill old process before restart (motor, encoder)
- Motors need ≥25% PWM → threshold coded in node
- ENA/ENB miswired → rewired to align with IN pins
- Front wheels spun backwards → swapped motor lead polarity
- Front/back turning inversion → breadboard second output wire per GPIO row
- Count-only encoders cannot sense direction → fused from /cmd_vel
- Zero-cmd direction flip → deadband patch (|cmd| &gt; 0.01)
- tflite-runtime has no Python 3.12 wheels → ai-edge-litert; NumPy pinned to 1.26.4
- Camera device number changes after reboot → re-verify /dev/videoN
- WSL cannot SSH to Pi on hotspot → use Windows PowerShell
- BNO055 tilted ~18° → remount flat before nav2; mag calibrate before demo
- GPS no fix indoors → normal; test outdoors with sky view
- Dashboard `NameError: requests` → verify with `grep` after editing
- Dashboard `TypeError: function not iterable` → `stream_with_context(gen())`
- Dashboard iframe 404 → check access log for stray quotes in src attribute
- Browser cache stale → incognito + Ctrl+Shift+R
- Port 8080 blocked → `pkill -f app.py`, verify with `curl -I`

## Notes for Report

- Chassis is open-source adapted (Thingiverse), not designed from scratch —
  **must cite original source** in references
- Custom work: Pi mounting tray, camera mast, two-deck layout, wiring integration,
  breadboard signal-sharing architecture, encoder odometry with cmd_vel direction
  fusion + deadband patch, BNO055 NDOF integration, Mission Control dashboard
  (unified sensor strip + camera proxy + embedded drive pad)
- "Future improvements" section: deferred sensors (rain, soil, air quality),
  solar panel, IP54 enclosure, BMP280 pressure integration
- PlantVillage dataset © original authors (CC BY-SA) — attribute in report
- Known demo caveat: phone-screen leaf images may misclassify (LCD moiré)
- Encoder limitation: ±10% per-leg accuracy; EKF + GPS fusion will correct drift
- BNO055 substitution: shop sent BNO055 instead of MPU9250; kept because onboard
  fusion processor simplifies stack
