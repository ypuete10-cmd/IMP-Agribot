# Build Log

Dated progress log with photos. Newest entries at the top.

---

## 08/10/2026 — Sensor stack COMPLETE (IMU + GPS + encoder fixes)

Wired and verified all three sensors: 4× encoders, BNO055 IMU, NEO-8M GPS.
Sensor stack is now fully live and publishing to ROS2 topics.

**BNO055 IMU** (`imu_node.py`) — I2C bus 1 at address `0x29` (address
pin high). Chip ID `0xa0` confirmed this is a BNO055, not the MPU9250
originally ordered. Kept deliberately: onboard fusion processor outputs
ready quaternion (no Madgwick needed). NDOF mode `0x0C`, publishes
`/imu/data` at 20 Hz:

| Field | Register | Scale |
|-------|----------|-------|
| Orientation quaternion | 0x20 | 1/16384 |
| Angular velocity (gyro) | 0x14 | 1/16 → rad/s |
| Linear acceleration | 0x28 | 1/100 → m/s² |

Covariances set for `robot_localization`. Verified: quaternion responds
smoothly to yaw, gyro noise ~0.005 rad/s at rest, gravity on Z-axis.
**Note:** board currently tilted ~18° (x=-3.1 m/s² at rest) — must
remount flat before nav2.

**NEO-8M GPS** (`gps_node.py`) — `/dev/ttyAMA0` @ 9600 baud, parses
`$GPGGA`/`$GNGGA` sentences. Publishes `/fix` (NavSatFix) at 1 Hz
**always**: status `-1` + `0.0/0.0` when no fix, real lat/lon +
`STATUS_FIX` when locked. Verified indoors: stream healthy, status `-1`
as expected (needs sky view for position fix). Requires `pyserial`.

**Pi config for UART** (both required on Pi 5 + Ubuntu 24.04):
```bash
sudo nano /boot/firmware/config.txt
# Add BOTH:
enable_uart=1
dtparam=uart0=on
```
`/dev/ttyAMA0` = GPIO header UART. `/dev/ttyAMA10` = Bluetooth — ignore.
Also remove serial console from `cmdline.txt`, and add user to `dialout`
group: `sudo usermod -aG dialout $USER`.

**Encoder fixes** (`encoder_node.py`) — direction now fused from
`/cmd_vel` using the same diff-drive mixing as `motor_driver` (per-side,
not per-wheel). **Deadband patch:** `|cmd| &lt;= 0.01` keeps the last
direction — stops coasting ticks being miscounted at stops/reversals.
Verified: stable plateaus at rest (zero phantom drift), smooth
bidirectional integration. Calibration: `ticks_per_meter ~90`.

**Sensor stack status:**

| Sensor | Topic | State |
|--------|-------|-------|
| 4× encoders | `/odom`, `/wheel_ticks` | calibrated, signed odometry |
| BNO055 IMU | `/imu/data` | fused quaternion, 20 Hz |
| NEO-8M GPS | `/fix` | publishing; fix needs sky view |

**GPIO/I2C/UART budget (final):**
- Motors: 12/16/20 (L), 18/25/26 (R)
- Encoders: 5/6/13/19
- I2C: GPIO2/3 → BNO055 @0x29 (AHT20 0x38 + BMP280 0x76 share later)
- UART: GPIO14/15 → `/dev/ttyAMA0` → GPS
- **Spare: 12 GPIO** (4/7/8/9/10/11/17/21/22/23/24/27)

**Next:** `robot_localization` EKF (`/odom` + `/imu/data` →
`/odometry/filtered`), then nav2 with GPS waypoints. Demo-day checklist:
remount IMU flat, GPS antenna sky view, figure-8 mag calibration for
BNO055.



---

## 07/10/2026 — Encoder odometry complete (4-wheel, cmd_vel direction fusion)

Wired 4× LM393 encoder modules (VCC 3.3V Pin 1, GND blue rail, D0 to
GPIO 5/6/13/19). D0 used; A0 unconnected. Pull-up enabled in software.

`encoder_node.py` publishes:
- `/wheel_ticks` (Int32MultiArray, per-wheel cumulative counts, 10 Hz)
- `/odom` (nav_msgs/Odometry + odom→base_link TF, 10 Hz)

**Direction fusion:** encoders are count-only (single channel), so
direction is inferred from `/cmd_vel` using the same diff-drive mixing
as `motor_driver`. This is the standard approach used by
robot_localization. A **deadband patch** prevents zero commands from
flipping direction sign — stops coasting ticks from being counted
backwards.

**Calibration:** ticks_per_meter = 90.0. Measured at 80.0 setting:
1.128 odom per 1.00 m actual. 64 ticks/rev hand-measured.

**Performance:** zero drift at rest (stable plateaus), smooth
bidirectional integration, ±10% distance accuracy per leg. Documented
as a known limitation — GPS fusion in nav2 will correct drift globally.

**Issues fixed during bring-up:**
1. GPIO busy on restart → `pkill -f encoder_node` before relaunch
2. Count-only encoders cannot sense direction → fused from `/cmd_vel`
3. Zero-cmd direction flip → deadband patch (`|cmd| &gt; 0.01` updates dir)
4. `calibrate.py` script retired → prompt timing confused leg boundaries;
   live streaming `ros2 topic echo /odom` is the reliable method

**GPIO budget now:** 14 used, 12 spare
- Motors: 12/16/20 (left), 18/25/26 (right)
- Encoders: 5/6/13/19
- Reserved: 14/15 (GPS UART), 2/3 (I2C IMU + env sensors)
- Spare: 4/7/8/9/10/11/17/21/22/23/24/27

![Encoder modules wired — LM393 D0 to GPIO 5/6/13/19, 3.3V VCC](https://github.com/user-attachments/assets/9fffb2ad-3112-46aa-88a6-0cb6f2c4303b)

![Encoder test — terminal showing /odom topic with forward and return counts](https://github.com/user-attachments/assets/6c747bc8-e93b-446b-8147-97b6f27c1fd0)

---

## 06/10/2026 — Web drive dashboard + one-command bringup

Added `bringup.launch.py` — one command starts motor_driver,
rosbridge_server, and Flask camera_stream + dashboard together:
`ros2 launch robot_control bringup.launch.py`. Ctrl+C stops everything
cleanly, preventing the GPIO-busy orphan issue.

Built `control.html` web drive page (served at /control):
- Buttons + WASD/arrow keys + speed slider + embedded camera feed
- roslib.js → WebSocket → rosbridge (port 9090) → publishes /cmd_vel
  at 10 Hz while held (matches the 1 s motor watchdog)
- Auto-stop on button release / tab blur
- No hardcoded IP — uses `location.hostname`, survives hotspot IP changes

Updated `camera_stream.py` with `@app.route('/control')`.
Updated `setup.py` with launch `data_files` entry (share/robot_control/launch).
Updated `Pi_5_Command_Reference.docx` to v6Oct (Section 12 Web Drive
Control, motors marked DONE, bringup in Section 8, 5 new quick fixes).

Hardware already verified: 4-wheel drivetrain (forward, turn-in-place
left/right all correct). Architecture: one L298N channel per wheel,
breadboard signal sharing, all 4 ENA/ENB jumpers off.

![L298N wiring close-up — GPIO 12/16/20 connected, red power LED on](https://github.com/user-attachments/assets/10d18684-0527-4309-abd0-4ec2ced57a15)

![Pi 5 mounted on standoffs with L298N drivers and power wiring](https://github.com/user-attachments/assets/6ef2a59a-cf37-44f9-af28-829e5eb57678)

---

## 03/10/2026 — 4-wheel drive complete (dual L298N per-channel wiring)

Wired the second L298N (right side). Final architecture: **front L298N
drives front-left (channel A) + front-right (channel B); back L298N
drives rear-left (channel A) + rear-right (channel B)** — one channel
per wheel, no motors in parallel (avoids exceeding 2A channel rating if
one motor stalls).

**Signal sharing via breadboard:** 6 GPIO signals each feed the same
channel letter on BOTH boards through breadboard junction rows:
- GPIO12 (Pin 32) → ENA on both boards (left speed, PWM)
- GPIO16 (Pin 36) → IN1 both; GPIO20 (Pin 38) → IN2 both (left direction)
- GPIO18 (Pin 12) → ENB on both boards (right speed, PWM)
- GPIO25 (Pin 22) → IN3 both; GPIO26 (Pin 37) → IN4 both (right direction)
- All 4 ENA/ENB jumpers removed (Pi PWM controls speed)

**Power distribution via breadboard rails:** buck IN− → blue rail → both
L298N GND + Pi Pin 6 (common ground); buck OUT+ (5V) → red rail → both
L298N +5V logic; L298N +12V tapped from buck IN+ screw terminal. Pi 5
still powered separately via USB-C.

**Issues fixed during bring-up:**
1. ENA/ENB wires landed on wrong header pins → rewired to align with IN pins
2. Front wheels spun backwards → swapped motor lead polarity on front board
3. Front/back turning inversion → added second output wire per breadboard
   row so every GPIO reaches the same lettered pin on both boards

**Test results:** forward (linear.x=0.5) — all 4 wheels correct;
turn-in-place (angular.z=0.5) — left/right counter-rotate correctly.
`motor_driver.py` required **zero code changes**.

![Completed wiring — Pi 5, dual L298N, breadboard signal sharing](https://github.com/user-attachments/assets/452b5b4d-3c04-4d60-8cad-738eb7868a78)

![Breadboard junction rows — GPIO 12/16/18/20/25/26 split to both boards](https://github.com/user-attachments/assets/ff44e6ab-d12a-4a93-bf8c-5e72cf7696f4)

![All four wheels with power and signal wiring](https://github.com/user-attachments/assets/400571d8-c496-4c05-a628-9dad00e9824d)

---

## 02/10/2026 — Motor driver first run (left side)

First successful motor power-up. L298N #1 wired to GPIO 12 (ENA/PWM),
16 (IN1), 20 (IN2) driving both left motors. `motor_driver` node
subscribes to /cmd_vel; teleop_twist_keyboard drives the wheels.

Two fixes discovered during bring-up:
- Motors need minimum ~25% PWM to overcome static friction — threshold
  coded into motor_driver.py
- GPIO busy error on restart — old motor_driver process must be killed
  before relaunching

Power from 12V wall adapter via HW-688 buck converter (12V→5V logic).
Right side (L298N #2) GPIO pins assigned, wiring next.

![L298N wiring close-up — GPIO 12/16/20 connected, red power LED on](https://github.com/user-attachments/assets/10d18684-0527-4309-abd0-4ec2ced57a15)

![Pi 5 mounted on standoffs with L298N drivers and power wiring](https://github.com/user-attachments/assets/6ef2a59a-cf37-44f9-af28-829e5eb57678)

---

## 01/10/2026 — Model retrained and deployed (domain-gap fix)

Retrained MobileNetV3-Small with 16 classes (15 diseases + Other
background), trimming the Other class to 800 images to fix the
over-prediction bias found last week. Webcam leaf captures were sorted
into their class folders and included in the training set alongside the
rebalanced Other class. Final val_accuracy: 90.13%
(10 frozen + 5 fine-tune epochs). Converted to TFLite float16
(1,876 KB) and deployed to the Pi 5.

End-to-end verification: clear leaf images classify at 96–99%
confidence; walls/desks correctly rejected as Other /
unknown_no_plant (0.60 threshold); /plant_health topic publishes
{class, confidence} JSON as designed.

Known issue noted for report: leaf images shown on a phone screen
occasionally misclassify due to LCD moiré — printed photos or real
leaves recommended for the demo.

![Training run - 16-class retrain reaching 90.1% val accuracy](https://github.com/user-attachments/assets/1e81b9d5-9931-424b-b7f9-241992538e5b)

![TFLite model exported - 1876 KB](https://github.com/user-attachments/assets/34875b44-1194-40c1-ae49-b44538a3f968)

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
