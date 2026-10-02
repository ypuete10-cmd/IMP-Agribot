# Project Status

**Yvette Lee EnQi (25034155)** — Autonomous Agricultural Robot for Crop Health Monitoring
Last updated: 2 October 2026 · Viva: 2 December 2026

---

## Repo Structure

```
robot_control/
├── robot_control/
│   ├── motor_driver.py      # subscribes /cmd_vel, PWM + dir control
│   ├── camera_stream.py     # Flask MJPEG stream (port 5000)
│   ├── capture.py           # single photo capture
│   ├── ai_inference.py      # TFLite inference, publishes /plant_health
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
5. Motor driver node on /cmd_vel; teleop drives **left side** (right L298N
   not yet wired)
6. GitHub sync working (Pi + web edits merged)

## Hardware Status

| Item | Status |
|------|--------|
| Pi 5 (Ubuntu 24.04, ROS2 Jazzy) | ✅ Running |
| USB webcam (/dev/video0) | ✅ Working (Pi Cam v2 retired — Ubuntu 24.04 incompatible) |
| L298N #1 (left motors) | ✅ Wired, spinning (min 25% PWM for static friction) |
| L298N #2 (right motors) | ⚠️ GPIO assigned, **not wired** |
| 3S LiPo 5500mAh | Purchased; running on 12V wall adapter until charger/safe bag arrive |
| NEO-8M GPS | Purchased, not wired (UART) |
| MPU9250 IMU | Purchased, not wired (I2C) |
| AHT20 + BMP280 | Purchased, not wired (I2C) |
| 4× wheel encoders | Purchased, not wired |

## Critical Path (remaining ~9 weeks)

1. Wire L298N #2 → full 4-wheel drive teleop
2. Wire GPS (UART, enable_uart=1) → verify /fix topic
3. Wire IMU + env sensors (I2C) → verify i2cdetect 0x68/0x38/0x76
4. Wire encoders → odometry for nav2
5. Dashboard: replace simulated scans with real GPS + /plant_health
6. nav2 + EKF integration
7. Report writing + demo prep

## GPIO Pinout

| GPIO | Pin | Function | Status |
|------|-----|----------|--------|
| 12 | 32 | L298N #1 ENA (PWM, left) | ✅ Wired |
| 16 | 36 | L298N #1 IN1 | ✅ Wired |
| 20 | 38 | L298N #1 IN2 | ✅ Wired |
| 18 | 12 | L298N #2 ENA (PWM, right) | ⬜ Not wired |
| 25 | 22 | L298N #2 IN1 | ⬜ Not wired |
| 26 | 37 | L298N #2 IN2 | ⬜ Not wired |
| 2/3 | 3/5 | I2C (IMU, AHT20, BMP280) | ⬜ Not wired |
| 14/15 | 8/10 | UART (GPS) | ⬜ Not wired |

## Known Issues / Fixes Applied

- Pi Camera v2 incompatible with Ubuntu 24.04 → USB webcam (V4L2)
- GPIO busy error → kill old motor_driver process before restart
- Motors need ≥25% PWM to overcome static friction → threshold coded in node
- tflite-runtime has no Python 3.12 wheels → ai-edge-litert; NumPy pinned to 1.26.4
- Camera device number changes after reboot → re-verify /dev/videoN before use
- WSL cannot SSH to Pi on hotspot → use Windows PowerShell

## Notes for Report

- Chassis is open-source adapted (Thingiverse), not designed from scratch —
  **must cite original source** in references
- Custom work: Pi mounting tray, camera mast, two-deck layout, wiring integration
- "Future improvements" section: deferred sensors (rain, soil, air quality),
  solar panel, IP54 enclosure
- PlantVillage dataset © original authors (CC BY-SA) — attribute in report
- Known demo caveat: phone-screen leaf images may misclassify (LCD moiré) —
  use printed photos or real leaves for the viva demo
