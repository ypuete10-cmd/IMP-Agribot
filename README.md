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

**AI inference** — on-device classification at ~80% validation accuracy:

![AI inference node classifying a leaf](https://github.com/user-attachments/assets/dd88a62d-1c6f-4a28-9630-d1e47c4b6f4f)

**Performance** — TFLite on Pi 5 CPU, no accelerator needed:

![TFLite benchmark: 3.5 ms/frame, 282 FPS](https://github.com/user-attachments/assets/e3fa8fbb-48d4-4445-a93a-bd0293608a8d)

**Farmer dashboard** — results table + GPS health map:

![Farmer dashboard](https://github.com/user-attachments/assets/dc5bf120-d234-43b8-aae1-257221774d6b)

## Mechanical Design

Chassis designed in CAD and printed in PETG (Bambu Studio, 3mm plate):

<img width="480" alt="Chassis top plate CAD - top view" src="https://github.com/user-attachments/assets/3de96f72-d851-41a3-9a6b-7fd785bcbb6a" />

<img width="480" alt="Chassis top plate CAD - isometric view" src="https://github.com/user-attachments/assets/35788aeb-f472-4bd1-aeed-3a147f56d40a" />

Assembled robot chassis with motors, standoffs, and wiring (as of 28/09/2026):

<img width="250" alt="Assembled chassis - side view" src="https://github.com/user-attachments/assets/21a81106-3c20-4bac-8320-a7bd5558f4b0" />

<img width="250" alt="Assembled chassis - top view" src="https://github.com/user-attachments/assets/6ef3bd7a-be48-4ab2-8ec2-26584f57cbb2" />

<img width="250" alt="Assembled chassis - wiring side view" src="https://github.com/user-attachments/assets/c0d88cbf-be35-4277-85a5-47282b713ea5" />

<img width="250" alt="Chassis earlier build state - 25 Sep" src="https://github.com/user-attachments/assets/90feef26-fb92-47be-a35c-5228b35c2a56" />

<img width="250" alt="midsection view" src="https://github.com/user-attachments/assets/97137316-677a-4c25-9b32-94fe4dc48960" />

<img width="250" alt="overall temporary view" src="https://github.com/user-attachments/assets/05d72e1d-3694-49c9-a5b1-b1866c871490" />


## Repository Structure

```
robot_control/
├── robot_control/        # ROS2 nodes (camera, motors, AI inference)
├── dashboard/            # Flask dashboard + result logger
└── training/             # PlantVillage training pipeline scripts
```





```
