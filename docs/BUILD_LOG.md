# Build Log

Dated progress log with photos. Newest entries at the top.

---

## 30/09/2026 — Electronics installation + live inference test

Pi 5, both L298N motor drivers, and webcam installed on the top deck.
Sensor breakout boards mounted at front. Ran live end-to-end inference
test — robot camera classifying a leaf image displayed on a phone
(Tomato___Late_blight, 81.8% confidence; Other/unknown_no_plant
rejections working).

![Live inference test](https://github.com/user-attachments/assets/b16aba8d-723a-4b9d-9569-3d3ec4cedd94)

![Electronics - front view](https://github.com/user-attachments/assets/ea28d17e-35fe-4968-83a4-e7e658e6c000)

![Electronics - side view](https://github.com/user-attachments/assets/859d60d4-1d47-4234-96a9-194b9f0fc6f0)

![Electronics - front sensor boards](https://github.com/user-attachments/assets/508679ed-d6a9-49d9-ab35-5b2e6dd22362)

---

## 28/09/2026 — Chassis printed and assembled

Top plate designed in CAD, sliced in Bambu Studio, printed in PETG
(3mm plate). Chassis assembled with 4x TT motors, wheels, and standoffs.

![Chassis CAD - top view](https://github.com/user-attachments/assets/3de96f72-d851-41a3-9a6b-7fd785bcbb6a)

![Chassis CAD - isometric](https://github.com/user-attachments/assets/35788aeb-f472-4bd1-aeed-3a147f56d40a)

![Assembled - side view](https://github.com/user-attachments/assets/21a81106-3c20-4bac-8320-a7bd5558f4b0)

![Assembled - top view](https://github.com/user-attachments/assets/6ef3bd7a-be48-4ab2-8ec2-26584f57cbb2)

![Assembled - wiring side view](https://github.com/user-attachments/assets/c0d88cbf-be35-4277-85a5-47282b713ea5)

![Assembled - midsection](https://github.com/user-attachments/assets/97137316-677a-4c25-9b32-94fe4dc48960)

---

## 22/09/2026 — AI pipeline working

MobileNetV3-Small trained on 15-class PlantVillage subset (89.9% val
accuracy), retrained with background "Other" class (89.8%). TFLite
float16 model runs at 3.5 ms/frame (282 FPS) on the Pi 5 CPU.
`ai_inference` ROS2 node publishing to /plant_health verified end-to-end.

![AI inference node classifying a leaf](https://github.com/user-attachments/assets/dd88a62d-1c6f-4a28-9630-d1e47c4b6f4f)

![TFLite benchmark - 3.5 ms/frame, 282 FPS](https://github.com/user-attachments/assets/e3fa8fbb-48d4-4445-a93a-bd0293608a8d)
