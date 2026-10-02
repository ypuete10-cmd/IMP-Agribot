# IMP-AgriBot

**Autonomous agricultural robot for crop health monitoring.**
A Raspberry Pi 5–powered rover that navigates to GPS waypoints, captures plant
images, and classifies crop health on-device using a TFLite model — with
results displayed on a farmer-facing dashboard.

![AgriBot system](https://github.com/user-attachments/assets/dc5bf120-d234-43b8-aae1-257221774d6b)

---

## Hardware

| Component | Purpose |
|-----------|---------|
| Raspberry Pi 5 (Ubuntu 24.04, ROS2 Jazzy) | Main computer |
| USB Webcam (1080p) | Plant imaging |
| MobileNetV3-Small (TFLite, float16) | On-device disease classification |
| NEO-8M GNSS | Waypoint navigation |
| MPU9250 IMU + wheel encoders | Odometry & sensor fusion |
| 4× TT motors + L298N drivers | Differential drive |
| 3S LiPo 11.1V 5500mAh | Power (~3.5h runtime) |

## Software Architecture

- **ROS2 package `robot_control`** — camera stream, capture, motor driver,
  and AI inference nodes
- **AI pipeline** — PlantVillage → 16-class subset (15 diseases + Other) →
  MobileNetV3-Small transfer learning → TFLite float16 (~90% val accuracy)
- **Flask dashboard** — results table + GPS health map (auto-refresh)

## Results

**Live end-to-end test** — robot camera classifying a leaf displayed on
phone (30/09/2026):

![Live inference test - robot classifying leaf image on phone, terminal output](https://github.com/user-attachments/assets/b16aba8d-723a-4b9d-9569-3d3ec4cedd94)

**Performance** — TFLite on Pi 5 CPU, no accelerator needed:

![TFLite benchmark: 3.5 ms/frame, 282 FPS](https://github.com/user-attachments/assets/e3fa8fbb-48d4-4445-a93a-bd0293608a8d)

## Documentation

- **[Build Log](docs/BUILD_LOG.md)** — dated progress history with photos
- **[Project Status](docs/STATUS.md)** — current progress, GPIO pinout, critical path

## Repository Structure

```
robot_control/
├── robot_control/        # ROS2 nodes (camera, motors, AI inference)
├── dashboard/            # Flask dashboard + result logger
├── models/               # plant_health.tflite + class names
├── training/             # PlantVillage training pipeline scripts
└── docs/                 # Build log, status, command reference, figures
```
