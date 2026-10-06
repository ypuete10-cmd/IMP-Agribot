# Project Status

**Yvette Lee EnQi (25034155)** — Autonomous Agricultural Robot for Crop Health Monitoring
Last updated: 3 October 2026 · Viva: 2 December 2026

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
5. **4-wheel drive teleop** — dual L298N via breadboard signal sharing;
   forward and turn-in-place verified with teleop_twist_keyboard
6. GitHub sync working (Pi + web edits merged)

## Hardware Status

| Item | Status |
|------|--------|
| Pi 5 (Ubuntu 24.04, ROS2 Jazzy) | ✅ Running |
| USB webcam (/dev/video0) | ✅ Working (Pi Cam v2 retired — Ubuntu 24.04 incompatible) |
| Dual L298N motor drivers | ✅ Wired, 4-wheel drive working (breadboard signal sharing) |
| Breadboard (signal + power rails) | ✅ 6 GPIO → both boards; 5V/GND/12V distributed |
| 3S LiPo 5500mAh | Purchased; running on 12V wall adapter until charger/safe bag arrive |
| NEO-8M GPS | Purchased, not wired (UART) |
| MPU9250 IMU | Purchased, not wired (I2C) |
| AHT20 + BMP280 | Purchased, not wired (I2C) |
| 4× wheel encoders | Purchased, not wired |

## Critical Path (remaining ~8 weeks)

1. ~~Wire L298N #2 → full 4-wheel drive teleop~~ ✅ DONE 03/10
2. Wire GPS (NEO-8M) to UART, enable_uart=1, test /fix topic
3. Wire IMU + env sensors (I2C) → verify i2cdetect 0x68/0x38/0x76
4. Wire encoders → odometry for nav2
5. Dashboard: replace simulated scans with real GPS + /plant_health
6. nav2 + EKF integration
7. Report writing + demo prep

## GPIO Pinout

| GPIO | Pin | Function | Status |
|------|-----|----------|--------|
| 12 | 32 | ENA both boards (PWM, left speed) | ✅ Wired |
| 16 | 36 | IN1 both boards (left dir) | ✅ Wired |
| 20 | 38 | IN2 both boards (left dir) | ✅ Wired |
| 18 | 12 | ENB both boards (PWM, right speed) | ✅ Wired |
| 25 | 22 | IN3 both boards (right dir) | ✅ Wired |
| 26 | 37 | IN4 both boards (right dir) | ✅ Wired |
| 2/3 | 3/5 | I2C (IMU, AHT20, BMP280) | ⬜ Not wired |
| 14/15 | 8/10 | UART (GPS) | ⬜ Not wired |

## Known Issues / Fixes Applied

- Pi Camera v2 incompatible with Ubuntu 24.04 → USB webcam (V4L2)
- GPIO busy error → kill old motor_driver process before restart
- Motors need ≥25% PWM to overcome static friction → threshold coded in node
- ENA/ENB miswired during bring-up → rewired to align with IN pins
- Front wheels spun backwards → swapped motor lead polarity
- Front/back turning inversion → breadboard second output wire per GPIO row
- tflite-runtime has no Python 3.12 wheels → ai-edge-litert; NumPy pinned to 1.26.4
- Camera device number changes after reboot → re-verify /dev/videoN before use
- WSL cannot SSH to Pi on hotspot → use Windows PowerShell

## Notes for Report

- Chassis is open-source adapted (Thingiverse), not designed from scratch —
  **must cite original source** in references
- Custom work: Pi mounting tray, camera mast, two-deck layout, wiring integration,
  breadboard signal-sharing architecture (dual L298N per-channel)
- "Future improvements" section: deferred sensors (rain, soil, air quality),
  solar panel, IP54 enclosure
- PlantVillage dataset © original authors (CC BY-SA) — attribute in report
- Known demo caveat: phone-screen leaf images may misclassify (LCD moiré) —
  use printed photos or real leaves for the viva demo
