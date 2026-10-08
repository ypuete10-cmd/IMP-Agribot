# Pi 5 Command Reference

*Updated: 6 Oct 2026 — 4-wheel drivetrain complete (forward + turn verified), web drive dashboard via rosbridge, one-command bringup launch file*

Replace `[PI_IP]` with the actual Pi IP address. The IP changes when you switch networks. (Tip: the hostname `yvette-pi5.local` may also work from Windows browsers/SSH — try it if the IP changed and you don't want to look it up.)

---

## 1. SSH Access to Raspberry Pi 5

From Windows PowerShell (not WSL):

```bash
ssh yvette_pi@[PI_IP]
```

If SSH fails, the IP may have changed. Check on the Pi monitor:

```bash
ip addr show | grep "inet 10"
```

---

## 2. ROS2 Workspace (robot_control)

### Build after any code change

```bash
cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash
```

### Auto-source on every login (already done)

```bash
echo "source /opt/ros/jazzy/setup.bash" &gt;&gt; ~/.bashrc
echo "source ~/ros2_ws/install/setup.bash" &gt;&gt; ~/.bashrc
```

After this, every new terminal loads ROS2 and the workspace automatically. You only need `cd ~/ros2_ws` when building.

&gt; **Note:** The farmer dashboard (Section 11) does NOT need colcon build — run its scripts directly with python3. It is not a ROS2 package.

---

## 3. Camera Commands (USB Webcam)

*Project uses a USB webcam (1080p, plug-and-play V4L2). The Pi Camera Module v2 was retired: on Ubuntu 24.04 it requires compiling the whole libcamera stack from source — not worth the project time.*

*IMPORTANT: The device number changes after reboot (the Pi internal camera ISP creates dummy devices /dev/video0–7). Always re-verify before assuming a number. As of 22 Sep the webcam is on /dev/video0.*

### Live stream to browser

```bash
ros2 run robot_control camera_stream
```

Then open in laptop browser: `http://[PI_IP]:5000`

### Capture single photo

```bash
ros2 run robot_control capture_image
ros2 run robot_control capture_image waypoint_1.jpg
```

### Find which /dev/video device the camera is on

```bash
python3 -c "
import cv2
for i in range(10):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        ret, frame = cap.read()
        print(f'/dev/video{i}: read={ret}')
        cap.release()
"
```

### Test camera directly (no ROS2)

```bash
python3 -c "import cv2; cap=cv2.VideoCapture(0); ret,frame=cap.read(); cv2.imwrite('test.jpg', frame); cap.release(); print('Saved test.jpg')"
```

&gt; **Note:** Only one node can hold the camera at a time. If camera_stream or ai_inference is running, kill it before opening the camera elsewhere.

---

## 4. AI Inference (TFLite on Pi 5 CPU)

*The trained model (MobileNetV3-Small, 16 classes incl. background "Other") runs on the Pi CPU via ai-edge-litert. Measured: 3.5 ms/frame, 282 FPS — no Coral TPU needed.*

### Run the inference node

```bash
ros2 run robot_control ai_inference
ros2 topic echo /plant_health
```

Output looks like:

```
data: '{"class": "Tomato___Late_blight", "confidence": 0.893}'
```

### Useful parameters

```bash
ros2 run robot_control ai_inference --ros-args -p interval_sec:=0.5
ros2 run robot_control ai_inference --ros-args -p camera_index:=2
```

| Parameter | Default | Meaning |
|-----------|---------|---------|
| model_path | /home/yvette_pi/plant_health.tflite | TFLite model location |
| class_names_path | /home/yvette_pi/class_names.json | Class label list |
| camera_index | 0 | Video device number — re-verify after reboot |
| interval_sec | 2.0 | Seconds between classifications |

### Runtime install notes (already done)

Ubuntu 24.04 ships Python 3.12; the old tflite-runtime package has no 3.12 wheels. Installed Google's successor instead:

```bash
pip3 install ai-edge-litert --break-system-packages
```

ai-edge-litert conflicted with apt OpenCV (cv2) because it pulled NumPy 2.x while python3-opencv needs NumPy 1.x. Pinned NumPy:

```bash
pip3 install "numpy==1.26.4" --break-system-packages
```

Verify all three imports together:

```bash
python3 -c "import numpy, cv2, ai_edge_litert.interpreter as tflite; print('numpy', numpy.__version__, '| cv2 OK | litert OK')"
```

### Benchmark the model (standalone test)

```bash
python3 ~/benchmark_tflite.py
# Expected: ~3.5 ms/frame | ~282 FPS
```

&gt; **Behavior notes:** results below 0.60 confidence are published as `unknown_no_plant` (safety net). The "Other" class covers walls/desks — trained on 800 negatives + 30 real webcam background shots.

---

## 5. Model Training Pipeline (Windows Laptop)

Training happens on the laptop (or Google Colab), NOT on the Pi. The Pi only runs inference.

### File locations on laptop

| File | Path |
|------|------|
| Full dataset (git clone) | C:\Users\yvett\PlantVillage-Dataset\raw\color |
| Training subset (16 classes) | C:\Users\yvett\plantvillage_subset |
| Webcam background shots | C:\Users\yvett\plantvillage_subset\Other |
| Webcam leaf shots (domain adaptation) | C:\Users\yvett\leaf_shots |
| Training script | C:\Users\yvett\train_plantvillage.py |
| TFLite converter | C:\Users\yvett\convert_tflite.py |
| Model test script | C:\Users\yvett\test_tflite.py |
| Subset builder | C:\Users\yvett\make_subset.py |
| Background builder | C:\Users\yvett\make_background.py |
| Other-folder trimmer | C:\Users\yvett\trim_other.py |
| Trained model | C:\Users\yvett\plant_health.tflite |
| Class names | C:\Users\yvett\class_names.json |

### Retrain workflow (after adding new images)

```bash
python C:\Users\yvett\trim_other.py
python C:\Users\yvett\train_plantvillage.py
python C:\Users\yvett\convert_tflite.py
```

### Deploy new model to Pi

```powershell
scp C:\Users\yvett\plant_health.tflite C:\Users\yvett\class_names.json yvette_pi@[PI_IP]:~/
```

Then on Pi, also copy into the repo's models/ folder:

```bash
cp ~/plant_health.tflite ~/class_names.json ~/ros2_ws/src/robot_control/models/
```

Expected training results so far: 15-class model 89.9% val accuracy; 16-class (with Other) 89.8% → 90.1% val accuracy after domain-gap fix. Lab-image test: Tomato___Late_blight 89.3% / 87.5%.

---

## 6. File Transfer (Pi ↔ Windows Laptop)

Run scp in Windows PowerShell. On Windows, always use the full path (`C:\...`) — the `~` shorthand is NOT expanded on the Windows side (it works on the Pi side).

### Pi → Laptop

```powershell
scp yvette_pi@[PI_IP]:~/plant_photo.jpg C:\Users\yvett\Downloads\
scp yvette_pi@[PI_IP]:~/ros2_ws/src/robot_control/robot_control/*.py C:\Users\yvett\Downloads\
scp -r yvette_pi@[PI_IP]:~/plant_images C:\Users\yvett\Downloads\
```

### Laptop → Pi

```powershell
scp C:\Users\yvett\plant_health.tflite yvette_pi@[PI_IP]:~/
scp C:\Users\yvett\make_subset.py yvette_pi@[PI_IP]:~/
```

---

## 7. System & Hardware Checks

### Check Pi IP address

```bash
ip addr show | grep "inet 10"
```

### Check camera detection

```bash
ls /dev/video*
v4l2-ctl --list-devices
```

### Test I2C bus (AHT20, MPU9250, BMP280)

```bash
sudo i2cdetect -y 1
```

- 0x38 = AHT20 (temperature/humidity)
- 0x68 = MPU9250 IMU
- 0x76 = BMP280 (pressure)

### Check ROS2 topics

```bash
ros2 topic list
ros2 topic echo /plant_health
ros2 topic echo /fix
ros2 topic echo /imu/data
ros2 topic echo /cmd_vel
```

### Check disk space

```bash
df -h
```

### Check battery voltage (if ADS1115 wired)

```bash
python3 ~/battery_monitor.py
```

---

## 8. Running ROS2 Nodes

**RECOMMENDED (6 Oct): use the bringup launch file — one terminal starts motor driver + rosbridge + camera stream/dashboard together:**

```bash
cd ~/ros2_ws
colcon build --symlink-install  # only needed after code changes
source install/setup.bash
ros2 launch robot_control bringup.launch.py
```

Ctrl+C in that terminal stops everything cleanly (this also prevents the 'GPIO busy' error from orphaned motor_driver processes).

Manual mode (one terminal per node) is still useful while debugging:

```bash
# Terminal 1 — Camera stream (port 5000) + dashboard page (/control)
ros2 run robot_control camera_stream

# Terminal 2 — AI inference (publishes /plant_health)
ros2 run robot_control ai_inference

# Terminal 3 — Motor driver
ros2 run robot_control motor_driver

# Terminal 4 — rosbridge (needed for the web drive dashboard)
ros2 launch rosbridge_server rosbridge_websocket_launch.xml

# Terminal 5 — Monitor
ros2 topic list
ros2 topic echo /plant_health
ros2 topic echo /cmd_vel

# Terminal 6 — Keyboard teleop (drive with keys)
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

&gt; **Note:** camera_stream and ai_inference both want the webcam — run only one at a time for now (later: ai_inference subscribes to /camera/image_raw instead).

---

## 9. Motors (L298N + TT Motors) & Encoders

*Status (8 Oct): DONE — 4-wheel drivetrain + encoder odometry + IMU + GPS
all verified. Motors: forward + turn correct. Encoders: zero drift,
smooth bidirectional. IMU: BNO055 onboard fusion. GPS: /fix publishing.*

### Motor architecture (final, per-channel — no motors in parallel)

One channel per wheel:

| Board | Channel A (OUT1/OUT2) | Channel B (OUT3/OUT4) |
|-------|----------------------|----------------------|
| Front L298N | Front-LEFT wheel | Front-RIGHT wheel |
| Back L298N | Rear-LEFT wheel | Rear-RIGHT wheel |

### L298N pin map (BCM GPIO)

| Side | Signal | GPIO (BCM) | Pi physical pin |
|------|--------|-----------|-----------------|
| Left | ENA (speed PWM) — jumper removed | GPIO12 | Pin 32 |
| Left | IN1 | GPIO16 | Pin 36 |
| Left | IN2 | GPIO20 | Pin 38 |
| Right | ENB (speed PWM) — jumper removed | GPIO18 | Pin 12 |
| Right | IN3 | GPIO25 | Pin 22 |
| Right | IN4 | GPIO26 | Pin 37 |
| Both | L298N GND | — | common rail + Pi Pin 6 (GND) |

All 4 ENA/ENB jumpers removed. Signal sharing via breadboard.

### Encoder wiring (LM393, 3.3V, pull-up)

| Wheel | GPIO (BCM) | Pi physical pin | Wire |
|-------|-----------|-----------------|------|
| Front-Left | GPIO5 | Pin 29 | D0 (A0 unused) |
| Rear-Left | GPIO6 | Pin 31 | D0 |
| Front-Right | GPIO13 | Pin 33 | D0 |
| Rear-Right | GPIO19 | Pin 35 | D0 |

All encoder VCC → 3.3V Pin 1. All GND → breadboard blue rail.
`pull_up=True` in software.

### Run encoder node

```bash
ros2 run robot_control encoder_node
ros2 topic echo /wheel_ticks
ros2 topic echo /odom
```

Output: cumulative per-wheel counts (Int32MultiArray) and nav_msgs/Odometry
with odom→base_link TF at 10 Hz.

### Test motors (wheels off ground)

```bash
# Terminal 1 — start the driver
ros2 run robot_control motor_driver

# Terminal 2 — forward at 50%
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.5}, angular: {z: 0.0}}"

# Stop
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0}, angular: {z: 0.0}}"
```

### Keyboard driving (teleop)

```bash
sudo apt install ros-jazzy-teleop-twist-keyboard -y
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

### Motor bring-up issues (for report)

1. ENA/ENB wires landed on wrong header pins — rewired in line with IN pins
2. Front wheels spun backwards — swapped motor lead polarity on front board
3. Turn test inverted — signals split per-board instead of per-channel-letter;
   fixed by adding second output wire per breadboard row

### Encoder bring-up issues (for report)

1. GPIO busy on restart → `pkill -f encoder_node` before relaunch
2. Count-only encoders cannot sense direction → fused from `/cmd_vel`
3. Zero-cmd direction flip → deadband patch (`|cmd| &gt; 0.01` updates dir)
4. `calibrate.py` script retired — prompt timing confused leg boundaries;
   live streaming `ros2 topic echo /odom` is the reliable method

## 10. Battery & Power Wiring

Battery: 11.1V 3S 45C 5500mAh LiPo (purchased). Full charge is 12.6V — both the L298N and the buck converter accept it, so treat it as the 12V rail.

### Power chain

```
LiPo → barrel jack adapter
barrel + → buck converter IN+ → L298N #1 +12V AND L298N #2 +12V
barrel - → buck converter IN- → breadboard blue rail
buck OUT+ (5V) → breadboard red rail → L298N #1 +5V (VCC) AND L298N #2 +5V
buck OUT- → breadboard blue rail
blue rail: buck IN-, buck OUT-, both L298N GND, Pi Pin 6
Pi 5 → powered separately via USB-C (power bank)
```

### LiPo safety rules

- **Never charge unattended** — balance charger + LiPo safe bag, on a non-flammable surface.
- **Never discharge below 9.0V total** (3.0V per cell) — stop driving around 10.5V.
- **Disconnect immediately** if the pack gets hot, puffy, or smells sweet.
- **Never power the Pi from the buck converter AND USB-C at the same time.**
- **First power-up of any new wiring:** benchtop supply, 3A current limit, wheels off the ground.

---

## 11. Farmer Dashboard (Farmer-Facing UI)

Flask web dashboard: results table + GPS field health map. The robot writes results to a JSON file; the web page reads it and auto-refreshes.

### File structure

```
~/ros2_ws/src/robot_control/dashboard/
+-- app.py              # Flask server (port 8080)
+-- result_logger.py    # ROS2 node: writes scans to data/results.json
+-- data/results.json   # shared data file (robot writes, web reads)
+-- templates/index.html # web page (auto-refreshes every 5 s)
```

### Run — Terminal 1 (web server)

```bash
python3 ~/ros2_ws/src/robot_control/dashboard/app.py
```

### Run — Terminal 2 (robot scans)

```bash
source /opt/ros/jazzy/setup.bash
python3 ~/ros2_ws/src/robot_control/dashboard/result_logger.py
```

`result_logger` currently SIMULATES one waypoint scan every 10 s. In Week 6, `simulate_scan()` gets replaced with real GPS + classifier subscriptions.

### View on laptop

```
http://[PI_IP]:8080
```

- Port 8080 = farmer dashboard. Port 5000 = camera stream + drive controls. Do not mix them up.
- New scans appear within ~15 s (10 s scan interval + 5 s page poll). This lag is normal.
- The map loads tiles from OpenStreetMap — the viewing laptop needs internet.
- No colcon build needed; run dashboard scripts directly with python3.
- `dashboard/` lives inside the Git repo, so `git add .` picks it up automatically.

### Dashboard out of sync? Check

```bash
grep -c '"waypoint"' ~/ros2_ws/src/robot_control/dashboard/data/results.json
curl -s http://localhost:8080/api/stats
```

The two totals should match. Hard refresh the browser with Ctrl+Shift+R.

---

## 12. Web Drive Control (rosbridge Dashboard) — NEW 6 Oct

*Drive the robot from any browser (laptop or phone) on the same network. Buttons + WASD/arrow keys, speed slider, embedded camera feed, auto-stop on button release / tab blur. roslib.js talks WebSocket to rosbridge; no changes to motor_driver.py needed.*

### How it works

```
Browser (control.html, roslib.js)
    | WebSocket
    v
rosbridge_server on Pi (port 9090) ← started by bringup.launch.py
    | publishes /cmd_vel at 10 Hz while a button is held
    v
motor_driver node (watchdog stops motors 1 s after last message)
```

### Files

| File | Path on Pi |
|------|-----------|
| Control page | ~/ros2_ws/src/robot_control/dashboard/drive/control.html (served by Flask at /control) |
| Flask route | @app.route('/control') in camera_stream.py |
| rosbridge | ros-jazzy-rosbridge-suite (installed 6 Oct) |

### Use it

```bash
# Everything via bringup (recommended):
ros2 launch robot_control bringup.launch.py
```

Then open in a browser on the same network:

```
http://[PI_IP]:5000/control
```

The status badge must show **CONNECTED** (green). Hold a button to drive, release to stop. Verify the chain with:

```bash
ros2 topic echo /cmd_vel
```

&gt; **Note:** control.html uses `location.hostname` for the WebSocket and `iframe src="/"` for the camera — no hardcoded IP, so it survives hotspot IP changes. Try `http://yvette-pi5.local:5000/control` if the IP is unknown.

---

## 13. IMU (BNO055 I2C)

*Status (8 Oct): DONE. BNO055 at I2C address 0x29 (address pin high).
Chip ID 0xa0 confirmed. NDOF mode 0x0C, onboard fusion processor outputs
ready quaternion — simpler than MPU9250 + Madgwick. Publishes /imu/data
at 20 Hz.*

### Install dependency

```bash
pip3 install smbus2 --break-system-packages   # if not already installed
```

### Enable I2C (already done during initial setup)

```bash
sudo apt install i2c-tools -y
sudo usermod -aG i2c $USER
# Reboot after adding group
```

Verify the BNO055 is on the bus:

```bash
sudo i2cdetect -y 1
# Expected: 0x29 (BNO055)
```

### Run the IMU node

```bash
ros2 run robot_control imu_node
ros2 topic echo /imu/data
```

Output: `sensor_msgs/Imu` at 20 Hz with:
- **Orientation** — fused quaternion (register 0x20, scale 1/16384)
- **Angular velocity** — gyro in rad/s (register 0x14, scale 1/16 → dps → rad/s)
- **Linear acceleration** — in m/s² (register 0x28, scale 1/100)

Covariances are set for `robot_localization` EKF integration.

### Verify IMU is working

```bash
# Check quaternion responds to yaw
ros2 topic echo /imu/data | grep -A1 orientation

# Check gyro noise at rest (~0.005 rad/s is normal)
ros2 topic echo /imu/data | grep -A1 angular_velocity
```

### Important: mount flat before nav2

The BNO055 board is currently tilted ~18° (x=-3.1 m/s² at rest instead
of near-zero). Remount flat before running nav2/robot_localization, or
the gravity vector will bias the EKF. Also perform a figure-8 magnetic
calibration before the demo day for best heading accuracy.

### BNO055 vs MPU9250

The shop substituted BNO055 for the originally ordered MPU9250. Kept
deliberately: the BNO055 has an onboard fusion processor that outputs
a ready quaternion in NDOF mode. This eliminates the need for an
external sensor fusion library (e.g. Madgwick/Mahony), simplifying the
software stack. Trade-off: less raw-sensor transparency, but sufficient
for this project's accuracy requirements.

## 14. GPS (NEO-8M GNSS)

*Status (8 Oct): DONE. NEO-8M on /dev/ttyAMA0 @9600 baud, publishes
/fix (NavSatFix) at 1 Hz ALWAYS. Indoors: stream healthy, status=-1
(no fix) as expected. Outdoors: position fix when sky view available.*

### Pi 5 UART configuration (BOTH required)

```bash
sudo nano /boot/firmware/config.txt
# Add BOTH lines:
enable_uart=1
dtparam=uart0=on
```

Then remove serial console from cmdline:

```bash
sudo nano /boot/firmware/cmdline.txt
# Remove any console=serial0 or console=ttyAMA0 entries
```

Add user to `dialout` group and reboot:

```bash
sudo usermod -aG dialout $USER
sudo reboot
```

### Verify UART device

```bash
ls -la /dev/ttyAMA0
# Should exist and be readable by dialout group
```

**Note:** `/dev/ttyAMA0` = GPIO header UART (GPIO14/15).
`/dev/ttyAMA10` = Bluetooth — ignore.

### Install dependency

```bash
pip3 install pyserial --break-system-packages
```

### Run the GPS node

```bash
ros2 run robot_control gps_node
ros2 topic echo /fix
```

Output: `sensor_msgs/NavSatFix` at 1 Hz:
- **status = -1** (NO_FIX) + lat/lon = 0.0/0.0 when indoors/no satellites
- **status = 0** (FIX) + real lat/lon when sky view available

The node publishes **always** so downstream nodes (EKF, dashboard)
never wait on a silent topic.

### Verify GPS stream

```bash
# Check raw NMEA sentences directly
python3 -c "
import serial
s = serial.Serial('/dev/ttyAMA0', 9600, timeout=1)
for _ in range(5):
    print(s.readline().decode('ascii', errors='ignore').strip())
"
```

You should see `$GNGGA` or `$GPGGA` sentences.
## 15. Quick Fixes

### NumPy / OpenCV conflict (cv2 import crash with NumPy 2.x)

```bash
pip3 install "numpy==1.26.4" --break-system-packages
```

### Camera device number changed after reboot

```bash
# Find the working device number
python3 -c "
import cv2
for i in range(10):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        print(i, cap.read()[0])
        cap.release()
"
# Update all nodes (example: new device is 2)
sed -i 's/VideoCapture([0-9]*)/VideoCapture(2)/g' ~/ros2_ws/src/robot_control/robot_control/*.py
cd ~/ros2_ws && colcon build --symlink-install && source install/setup.bash
```

### "No executable found" error

```bash
cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash
```

### ROS2 not found in new terminal

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
```

### Fix broken apt packages

```bash
sudo apt --fix-broken install -y
```

### ROS2 install dependency conflict (liblz4/libzstd)

```bash
sudo apt install --allow-downgrades liblz4-1=1.9.4-1build1 libzstd1=1.5.5+dfsg2-2build1 -y
sudo apt install liblz4-dev libzstd-dev -y
sudo apt install ros-jazzy-ros-base python3-pip i2c-tools -y
```

### GPIO busy (lgpio.error) when starting motor_driver

```bash
pkill -f motor_driver
```
A stale motor_driver process is still holding the GPIO pins. Kill it, then rerun the node.

### Motors buzz but do not spin

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.5}, angular: {z: 0.0}}"
```
Below ~0.25 PWM the TT motors stall on static friction — motor_driver already boosts small commands to min_pwm 0.25. If they still stall: check L298N 12V power, all 4 ENA/ENB jumpers removed, and the common ground wire to Pi Pin 6.

### git push rejected (fetch first)

```bash
git pull origin main
git push origin main
```

### teleop_twist_keyboard not found

```bash
sudo apt install ros-jazzy-teleop-twist-keyboard -y
```

### apt install of rosbridge (or any ROS pkg) fails with 404

```bash
sudo apt update
sudo apt install ros-jazzy-rosbridge-suite -y
```
Stale cache: the repo published newer packages; update first, then install.

### Dashboard shows ERROR / DISCONNECTED

```bash
# rosbridge is not running. Either use bringup.launch.py, or manually:
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```

### 'bringup.launch.py was not found in the share directory'

```bash
cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash
```
Cause: build failed or aborted before copying the launch file into install/. Check setup.py has: `('share/' + package_name + '/launch', glob('launch/*.launch.py'))`, and the `launch/` folder exists in the package source.

### setup.py SyntaxError / NameError after editing

Common traps when adding the launch line by hand:
- Missing import: `from glob import glob`
- Typo: `find_package` → `find_packages`
- `os.path.join` used without: `import os`

Safest fix: rewrite setup.py completely from the known-good template (keep your console_scripts entry points).

---

## 16. Project File Locations on Pi

| File / Folder | Path on Raspberry Pi |
|---------------|----------------------|
| Camera stream node | ~/ros2_ws/src/robot_control/robot_control/camera_stream.py |
| Capture node | ~/ros2_ws/src/robot_control/robot_control/capture.py |
| AI inference node | ~/ros2_ws/src/robot_control/robot_control/ai_inference.py |
| Motor driver node | ~/ros2_ws/src/robot_control/robot_control/motor_driver.py |
| GPS node (ready, not yet deployed) | ~/ros2_ws/src/robot_control/robot_control/gps_node.py |
| Bringup launch file | ~/ros2_ws/src/robot_control/launch/bringup.launch.py |
| Web drive control page | ~/ros2_ws/src/robot_control/dashboard/drive/control.html (served at /control) |
| TFLite model | ~/ros2_ws/src/robot_control/models/plant_health.tflite |
| Class names | ~/ros2_ws/src/robot_control/models/class_names.json |
| Training scripts | ~/ros2_ws/src/robot_control/training/ |
| Dashboard server | ~/ros2_ws/src/robot_control/dashboard/app.py |
| Dashboard scan node | ~/ros2_ws/src/robot_control/dashboard/result_logger.py |
| Dashboard data | ~/ros2_ws/src/robot_control/dashboard/data/results.json |
| Dashboard web page | ~/ros2_ws/src/robot_control/dashboard/templates/index.html |
| Setup / entry points | ~/ros2_ws/src/robot_control/setup.py |
| Photos (default) | ~/plant_photo.jpg |
| Background shots | ~/bg_photos/ |
| Webcam leaf shots | ~/leaf_shots/ |
| Battery monitor | ~/battery_monitor.py |
| ROS2 workspace | ~/ros2_ws/ |
| Git repository | ~/ros2_ws/src/robot_control/ |

---

## 17. Status Snapshot (8 Oct 2026)

| Area | Status |
|------|--------|
| Camera + streaming | Done — USB webcam, stream + capture nodes working |
| AI model (train → TFLite → Pi inference) | Done — 90.1% val accuracy, 3.5 ms/frame on Pi CPU |
| Background class + confidence threshold | Done — retrained with Other class |
| Domain gap fix (webcam leaf shots) | Done — sorted into class folders |
| Farmer dashboard | Done — simulated scans; real GPS+AI hookup in Week 6 |
| Motors (4-wheel drivetrain) | **DONE** — all 4 wheels, forward + turn verified |
| Web drive control (rosbridge dashboard) | **Done** — browser buttons/WASD + camera feed at :5000/control |
| One-command bringup (launch file) | **Done** — bringup.launch.py starts motor + rosbridge + camera |
| Encoder odometry (4-wheel, signed, TF) | **DONE 7 Oct** — zero drift, ~90 ticks/m |
| IMU (BNO055 I2C fusion) | **DONE 8 Oct** — /imu/data at 20 Hz, onboard quaternion |
| GPS (NEO-8M UART /fix) | **DONE 8 Oct** — publishing always; fix needs sky view |
| robot_localization EKF | Not started |
| nav2 waypoint navigation | Not started |
| Dashboard real data hookup | Not started |
| Battery | Done — 11.1V 3S 45C 5500mAh LiPo purchased |
| Report + viva | 2 Dec 2026 |
