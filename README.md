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
- **AI pipeline** — PlantVillage → 15-class subset → MobileNetV3-Small
  transfer learning → TFLite float16
- **Flask dashboard** — results table + GPS health map (auto-refresh)

## Results

**AI inference** — on-device classification at ~89% validation accuracy:

![AI inference node classifying a leaf](https://github.com/user-attachments/assets/dd88a62d-1c6f-4a28-9630-d1e47c4b6f4f)

**Performance** — TFLite on Pi 5 CPU, no accelerator needed:

![TFLite benchmark: 3.5 ms/frame, 282 FPS](https://github.com/user-attachments/assets/e3fa8fbb-48d4-4445-a93a-bd0293608a8d)

**Farmer dashboard** — results table + GPS health map:

![Farmer dashboard](https://github.com/user-attachments/assets/dc5bf120-d234-43b8-aae1-257221774d6b)

## Repository Structure

```
robot_control/
├── robot_control/        # ROS2 nodes (camera, motors, AI inference)
├── dashboard/            # Flask dashboard + result logger
├── docs/figures/         # Logbook figures
└── training/             # PlantVillage training pipeline scripts
```
