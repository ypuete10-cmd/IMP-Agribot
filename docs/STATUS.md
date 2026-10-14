# Project Status

**Yvette Lee EnQi (25034155)** — Autonomous Agricultural Robot for Crop Health Monitoring
Last updated: 14 October 2026 · Viva: 2 December 2026

---

## Repo Structure

```
robot_control/
├── robot_control/
│   ├── motor_driver.py          # PWM differential drive, subscribes /cmd_vel
│   ├── camera_stream.py         # Flask MJPEG stream (port 5000)
│   ├── capture.py               # Single photo capture
│   ├── ai_inference.py          # TFLite inference, publishes /plant_health
│   ├── encoder_node.py          # 4-wheel encoders + odometry + TF
│   ├── imu_node.py              # BNO055 I2C IMU, publishes /imu/data
│   ├── gps_node.py              # NEO-8M UART GPS, publishes /fix
│   ├── env_node.py              # AHT30 I2C temp/humidity, publishes /env/*
│   ├── ultrasonic_node.py       # 2× HC-SR04, publishes /ultrasonic/front + /emergency_stop
│   └── waypoint_follower.py     # Indoor autonomous nav, subscribes /odometry/filtered
├── launch/
│   └── bringup.launch.py        # 9-node one-command bringup
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
   90.1% val accuracy, 3.5 ms/frame (282 FPS) on Pi 5 CPU
4. **Mission Control dashboard** (port 8080) — live sensor cards, embedded
   camera + drive pad, keyboard WASD/arrows, waypoint Save/Run/Stop buttons,
   GPS map, results table. All via rosbridge WebSocket. Zero hardcoded IPs.
5. **4-wheel drive teleop** — dual L298N via breadboard signal sharing
6. **One-command bringup** — 9 ROS nodes + rosbridge + camera stream
7. **Web drive control** — embedded in Mission Control + standalone `/control`
8. **Encoder odometry** — 4× LM393 encoders, /wheel_ticks + /odom + TF,
   ~90 ticks/m, ±10% per-leg, zero drift at rest
9. **BNO055 IMU** — I2C @0x29, NDOF mode, /imu/data at 20 Hz
10. **NEO-8M GPS** — UART /dev/ttyAMA0 @9600, /fix at 1 Hz always
11. **AHT30 environmental sensor** — /env/temperature + /env/humidity
12. **robot_localization EKF** — /odom + /imu/data → /odometry/filtered at 20 Hz
13. **Indoor waypoint navigation** — proportional follower, 15 cm tolerance,
    manual drive resumes after Stop via autonomous flag
14. **Ultrasonic emergency stop** — 2× HC-SR04 front sensors angled inward,
    /emergency_stop at &lt;30 cm, waypoint follower halts autonomous run

## Hardware Status

| Item | Status |
|------|--------|
| Pi 5 (Ubuntu 24.04, ROS2 Jazzy) | ✅ Running |
| USB webcam (/dev/video0) | ✅ Working (Pi Cam v2 retired) |
| Dual L298N motor drivers | ✅ Wired, 4-wheel drive working |
| Breadboard (signal + power rails) | ✅ 6 GPIO → both boards |
| 4× LM393 wheel encoders | ✅ Wired (GPIO 5/6/13/19) |
| BNO055 IMU (I2C 0x29) | ✅ Live, 20 Hz onboard fusion |
| NEO-8M GPS (UART /dev/ttyAMA0) | ✅ Publishing /fix; fix needs sky |
| AHT30 temp/humidity (I2C) | ✅ Live |
| 2× HC-SR04 ultrasonic | ✅ Wired (Trig 17/23, Echo 22/27), E-stop live |
| ros-jazzy-rosbridge-suite | ✅ Installed |
| robot_localization | ✅ EKF fusing encoders + IMU |
| 3S LiPo 5500mAh | Purchased; on 12V wall adapter until charger/safe bag |
| ADS1115 battery monitor | Not wired (when LiPo returns) |
| BMP280 pressure (I2C) | Purchased, not wired (shares bus) |
| MPU9250 (original order) | Shop substituted with BNO055 — kept deliberately |

## Critical Path (remaining ~7 weeks)

1. ~~4-wheel drive teleop~~ ✅ 03/10 · ~~Bringup + web drive~~ ✅ 06/10
2. ~~Encoder odometry~~ ✅ 07/10 · ~~IMU~~ ✅ 08/10 · ~~GPS~~ ✅ 08/10
3. ~~Mission Control dashboard~~ ✅ 09/10 · ~~EKF~~ ✅ 12/10
4. ~~Indoor waypoint navigation~~ ✅ 12/10 · ~~Ultrasonic E-stop~~ ✅ 14/10
5. **AI scan at each waypoint** (capture → classify → log to results.json) ← NEXT
6. **Field-test waypoint accuracy** on actual floor (tune gains if needed)
7. ADS1115 battery monitor (when LiPo returns)
8. Report writing + demo prep

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
| 17 | 11 | Ultrasonic Trig (left) | ✅ Wired |
| 23 | 16 | Ultrasonic Trig (right) | ✅ Wired |
| 22 | 15 | Ultrasonic Echo (left, via divider) | ✅ Wired |
| 27 | 13 | Ultrasonic Echo (right, via divider) | ✅ Wired |
| 2/3 | 3/5 | I2C (BNO055 @0x29, AHT30 share bus) | ✅ Live |
| 14/15 | 8/10 | UART /dev/ttyAMA0 (GPS) | ✅ Live |

**GPIO budget:** 18 used, 8 spare (4/7/8/9/10/11/21/24)

## Known Issues / Fixes Applied

- Pi Camera v2 incompatible with Ubuntu 24.04 → USB webcam (V4L2)
- GPIO busy error → kill old process before restart (motor, encoder)
- Motors need ≥25% PWM → threshold coded in node
- ENA/ENB miswired → rewired; front wheels backwards → swapped polarity;
  turning inversion → breadboard second output wire per GPIO row
- Count-only encoders → direction fused from /cmd_vel; zero-cmd flip → deadband
- tflite-runtime no Py3.12 wheels → ai-edge-litert; NumPy pinned 1.26.4
- Camera device number changes after reboot → re-verify /dev/videoN
- WSL cannot SSH to Pi on hotspot → use Windows PowerShell
- BNO055 tilted ~18° → remount flat before outdoor nav; mag calibrate before demo
- GPS no fix indoors → normal; test outdoors with sky view
- Dashboard bugs → verify edits with `grep`; `stream_with_context(gen())`;
  check access log for stray quotes; incognito + Ctrl+Shift+R; `pkill -f app.py`
- Waypoint JS outside `&lt;/script&gt;` → moved inside
- Dashboard/waypointFollower cmd_vel conflict → `autonomous` flag
- `lgpio.gpiochip_open(0)` fails on Pi 5 → `gpiochip_open(4)`
- bringup.launch.py syntax error → ultrasonic_node inserted inside navsat
  Node() call; closed navsat with `]),` first
- Dashboard full-file overwrites caused layout regressions → targeted
  additions only; restore from git if regressed

## Notes for Report

- Chassis is open-source adapted (Thingiverse), not designed from scratch —
  **must cite original source** in references
- Custom work: Pi mounting tray, camera mast, two-deck layout, wiring integration,
  breadboard signal-sharing architecture, encoder odometry with cmd_vel direction
  fusion + deadband patch, BNO055 NDOF integration, Mission Control dashboard,
  EKF config + encoder covariance tuning, indoor waypoint follower,
  **ultrasonic emergency stop safety chain** (sensor node + follower integration)
- Safety architecture worth a report paragraph: E-stop is topic-based
  (`/emergency_stop` Bool) so any future sensor (bump, IR) can feed the same chain
- "Future improvements" section: deferred sensors (rain, soil, air quality),
  solar panel, IP54 enclosure, BMP280/DHT11 integration
- PlantVillage dataset © original authors (CC BY-SA) — attribute in report
- Known demo caveat: phone-screen leaf images may misclassify (LCD moiré)
- Encoder limitation: ±10% per-leg accuracy; EKF + GPS fusion corrects drift
- BNO055 substitution: shop sent BNO055 instead of MPU9250; onboard fusion
  processor simplifies stack
- EKF drift: ~0.8 m per metre pushed without GPS loop closure — expected for
  dead-reckoning indoors; GPS standby ready via navsat_transform_node
