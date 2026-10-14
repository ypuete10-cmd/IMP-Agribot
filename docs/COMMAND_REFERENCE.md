# Pi 5 Command Reference

*Updated: 14 Oct 2026 — ultrasonic emergency stop live (2× HC-SR04, /emergency_stop chain), 9-node bringup, indoor stack complete. Next: AI scan at each waypoint.*

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

&gt; **Note:** The Mission Control dashboard (Section 11) does NOT need colcon build — run its scripts directly with python3. It is not a ROS2 package.

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

### Test I2C bus (BNO055, AHT30, BMP280)

```bash
sudo i2cdetect -y 1
```

- 0x29 = BNO055 (IMU, onboard fusion)
- 0x38 = AHT30 (temperature/humidity)
- 0x76 = BMP280 (pressure)

### Check ROS2 topics

```bash
ros2 topic list
ros2 topic echo /plant_health
ros2 topic echo /fix
ros2 topic echo /imu/data
ros2 topic echo /cmd_vel
ros2 topic echo /odometry/filtered
ros2 topic echo /ultrasonic/front
ros2 topic echo /emergency_stop
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

**RECOMMENDED: use the bringup launch file — one terminal starts the whole
robot stack:**

```bash
cd ~/ros2_ws
colcon build --symlink-install  # only needed after code changes
source install/setup.bash
ros2 launch robot_control bringup.launch.py
```

**Bringup now launches 9 ROS nodes + rosbridge + camera:**
- `motor_driver` — PWM motor control, subscribes /cmd_vel
- `encoder_node` — 4-wheel encoder counting + odometry + TF
- `imu_node` — BNO055 I2C IMU, publishes /imu/data
- `env_node` — AHT30 temp/humidity, publishes /env/*
- `gps_node` — NEO-8M UART GPS, publishes /fix
- `ekf_filter_node` — robot_localization, /odom + /imu/data → /odometry/filtered
- `navsat_transform_node` — GPS pipeline (standby; enable for outdoor use)
- `waypoint_follower` — indoor autonomous navigation + emergency stop handling
- `ultrasonic_node` — 2× HC-SR04 front sensors → /ultrasonic/front + /emergency_stop
- `rosbridge_server` — WebSocket bridge for dashboard
- `camera_stream` — Flask MJPEG on port 5000

Ctrl+C stops everything cleanly.

Then in a **second terminal**, start the Mission Control dashboard:

```bash
python3 ~/ros2_ws/src/robot_control/dashboard/app.py  # port 8080
```

Manual mode (one terminal per node) is still useful while debugging:

```bash
# Terminal 1 — Camera stream (port 5000) + standalone drive page (/control)
ros2 run robot_control camera_stream

# Terminal 2 — AI inference (publishes /plant_health)
ros2 run robot_control ai_inference

# Terminal 3 — Motor driver
ros2 run robot_control motor_driver

# Terminal 4 — Encoder odometry
ros2 run robot_control encoder_node

# Terminal 5 — IMU
ros2 run robot_control imu_node

# Terminal 6 — GPS
ros2 run robot_control gps_node

# Terminal 7 — Environmental sensor
ros2 run robot_control env_node

# Terminal 8 — EKF
ros2 run robot_localization ekf_node --ros-args --params-file ~/ros2_ws/src/robot_control/config/ekf.yaml

# Terminal 9 — Waypoint follower
ros2 run robot_control waypoint_follower

# Terminal 10 — Ultrasonic emergency stop
ros2 run robot_control ultrasonic_node

# Terminal 11 — rosbridge
ros2 launch rosbridge_server rosbridge_websocket_launch.xml

# Terminal 12 — Monitor
ros2 topic list
ros2 topic echo /odometry/filtered
ros2 topic echo /emergency_stop

# Terminal 13 — Keyboard teleop
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

&gt; **Note:** camera_stream and ai_inference both want the webcam —
&gt; run only one at a time for now.

---

## 9. Motors (L298N + TT Motors) & Encoders

*Status (14 Oct): DONE — 4-wheel drivetrain + encoder odometry + IMU + GPS + ultrasonic E-stop all verified.*

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

---

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

## 11. Mission Control Dashboard (Port 8080)

Unified farmer-facing web page: live sensor strip → camera + drive pad
→ GPS map + results table. All sensor data via `roslib.js` over the
rosbridge WebSocket (port 9090). Camera proxy routes have zero hardcoded
IPs.

**Controls:**
- **WASD / Arrow keys** — publish `/cmd_vel` at 10 Hz (same as drive pad)
- **Save Waypoint** — captures current EKF pose `{x, y, yaw}` to JSON
- **Clear All** — removes all saved waypoints
- **Run** — starts autonomous waypoint navigation
- **Stop** — halts autonomous mode, returns to manual drive control
- **`autonomous` flag** — prevents dashboard from publishing zero cmd_vel
  during Run (resolves conflict with waypoint_follower)

### File structure

```
~/ros2_ws/src/robot_control/dashboard/
+-- app.py              # Flask server (port 8080) + camera proxy
+-- result_logger.py    # ROS2 node: writes scans to data/results.json
+-- data/results.json   # shared data file
+-- templates/index.html # Mission Control page
```

### Camera proxy routes (no hardcoded IPs)

| Route | Returns |
|-------|---------|
| `GET /cam` | Wrapper HTML with `&lt;img src="/cam_feed"&gt;` |
| `GET /cam_feed` | MJPEG stream relayed from `127.0.0.1:5000/video_feed` |

### Run — Terminal 1 (robot stack)

```bash
cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash
ros2 launch robot_control bringup.launch.py
```

### Run — Terminal 2 (dashboard)

```bash
python3 ~/ros2_ws/src/robot_control/dashboard/app.py
```

### View on laptop

```
http://[PI_IP]:8080
```

- Port 8080 = Mission Control (sensors + camera + drive + waypoints + map + results)
- Port 5000 = camera stream only (including standalone `/control` drive page)
- The dashboard auto-refreshes sensor cards via rosbridge WebSocket
- New scan results appear in the table within ~15 s
- The map loads tiles from OpenStreetMap — viewing laptop needs internet
- No colcon build needed for dashboard changes; Flask auto-reloads `.py`
- **Edit the HTML with targeted changes only** — full-file overwrites have
  caused multiple layout regressions. Restore from git if regressed:
  `git checkout -- dashboard/templates/index.html` then re-apply additions.

### Dashboard out of sync? Check

```bash
ros2 node list | grep rosbridge          # rosbridge running?
ros2 topic hz /odom                       # sensor topics alive?
ros2 topic hz /odometry/filtered
curl -I http://localhost:8080/cam_feed    # camera proxy health
curl -I http://localhost:8080             # port not blocked (HTTP 200)
ros2 topic echo /emergency_stop           # E-stop chain alive
```

### Browser cache issues

If the page looks stale after a code update:
- Hard refresh: **Ctrl+Shift+R**
- Or open in **Incognito/Private** window

---

## 12. Web Drive Control

Two ways to drive from a browser:

**1. Mission Control dashboard (recommended)** — embedded drive pad at
`:8080` with all sensor cards visible.

**2. Standalone drive page** — served by `camera_stream.py` at
`:5000/control`. Lightweight, good for quick tests.

Both use `roslib.js` → WebSocket → rosbridge (port 9090) → publish
`/cmd_vel` at 10 Hz while a button is held. Auto-stop on release/blur.
Speed slider. WASD + arrow keys + on-screen buttons.

### Use it

```bash
ros2 launch robot_control bringup.launch.py
```

```
http://[PI_IP]:8080          # Mission Control
http://[PI_IP]:5000/control  # Standalone drive page
```

The status badge must show **CONNECTED** (green). Verify the chain with:

```bash
ros2 topic echo /cmd_vel
```

&gt; **Note:** both pages use `location.hostname` for the WebSocket and
&gt; relative paths for the camera — no hardcoded IP, so they survive
&gt; hotspot IP changes. Try `http://yvette-pi5.local:8080` if the IP is
&gt; unknown.

---

## 13. IMU (BNO055 I2C)

*Status (8 Oct): DONE. BNO055 at I2C address 0x29 (address pin high).
Chip ID 0xa0 confirmed. NDOF mode 0x0C, onboard fusion processor outputs
ready quaternion. Publishes /imu/data at 20 Hz.*

### Install dependency

```bash
pip3 install smbus2 --break-system-packages   # if not already installed
```

### Enable I2C (already done)

```bash
sudo apt install i2c-tools -y
sudo usermod -aG i2c $USER
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

### Verify IMU is working

```bash
ros2 topic echo /imu/data | grep -A1 orientation        # responds to yaw
ros2 topic echo /imu/data | grep -A1 angular_velocity   # ~0.005 rad/s noise at rest
```

### Important: mount flat before nav2

The BNO055 board is currently tilted ~18° (x=-3.1 m/s² at rest instead
of near-zero). Remount flat before running nav2/robot_localization outdoors,
or the gravity vector will bias the EKF. Also perform a figure-8 magnetic
calibration before the demo day.

### BNO055 vs MPU9250

The shop substituted BNO055 for the originally ordered MPU9250. Kept
deliberately: the BNO055 has an onboard fusion processor that outputs
a ready quaternion in NDOF mode. This eliminates the need for an
external sensor fusion library (e.g. Madgwick/Mahony), simplifying the
software stack. Trade-off: less raw-sensor transparency, but sufficient
for this project's accuracy requirements.

---

## 14. GPS (NEO-8M GNSS)

*Status (8 Oct): DONE. NEO-8M on /dev/ttyAMA0 @9600 baud, publishes
/fix (NavSatFix) at 1 Hz ALWAYS. Indoors: stream healthy, status=-1
as expected. Outdoors: position fix with sky view. navsat_transform_node
is in the bringup launch on standby for outdoor use.*

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

The node publishes **always** so downstream nodes never wait on a
silent topic.

### Verify GPS stream

```bash
python3 -c "
import serial
s = serial.Serial('/dev/ttyAMA0', 9600, timeout=1)
for _ in range(5):
    print(s.readline().decode('ascii', errors='ignore').strip())
"
```

You should see `$GNGGA` or `$GPGGA` sentences.

---

## 15. Quick Fixes

### NumPy / OpenCV conflict (cv2 import crash with NumPy 2.x)

```bash
pip3 install "numpy==1.26.4" --break-system-packages
```

### Camera device number changed after reboot

```bash
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

### GPIO busy (lgpio.error) when starting a GPIO node

```bash
pkill -f motor_driver
pkill -f encoder_node
pkill -f ultrasonic_node
```
A stale process is still holding the GPIO pins. Kill it, then rerun the node.

### `lgpio.gpiochip_open(0)` fails on Pi 5 ("chip not found")

Pi 5 exposes GPIO on **gpiochip 4**, not 0:

```python
h = lgpio.gpiochip_open(4)
```

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
Stale cache: update first, then install.

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
Cause: build failed or aborted before copying the launch file. Check setup.py has: `('share/' + package_name + '/launch', glob('launch/*.launch.py'))`.

### bringup.launch.py syntax error after adding a node

New node was inserted **inside** the previous node's `Node()` call —
the error points at a line *below* where you edited. Close the previous
entry completely with `]),` before starting the new node. Check
bracket/paren balance around every edit.

### setup.py SyntaxError / NameError after editing

Common traps when adding the launch line by hand:
- Missing import: `from glob import glob`
- Typo: `find_package` → `find_packages`
- `os.path.join` used without: `import os`

Safest fix: rewrite setup.py completely from the known-good template.

### Dashboard `NameError: name 'requests' is not defined`

```bash
grep "import requests" ~/ros2_ws/src/robot_control/dashboard/app.py
```
If missing, add it and save. Lesson: verify with grep after editing in
nano — unsaved buffers silently fail.

### Dashboard `TypeError: 'function' object is not iterable`

The `stream_with_context` call is missing parentheses:

```python
# WRONG
return Response(stream_with_context(gen), mimetype='multipart/x-mixed-replace')

# CORRECT
return Response(stream_with_context(gen()), mimetype='multipart/x-mixed-replace')
```

### Camera iframe 404 despite proxy healthy

Check the access log for a stray quote in the `src` attribute:

```bash
# Look for: GET /cam_feed" HTTP/1.1" 404
curl -I http://localhost:8080/cam_feed"
# Fix: remove the extra " from the iframe src in index.html
```

### Dashboard page looks stale after code update

- Hard refresh: **Ctrl+Shift+R**
- Or open in **Incognito/Private** window
- `app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0` is set in app.py

### Dashboard HTML layout regressed after an edit

Full-file overwrites caused multiple layout regressions. Restore the
last good version and re-apply only targeted additions:

```bash
git checkout -- dashboard/templates/index.html   # restore from last commit
git diff                                          # then re-apply your addition
```

### Port 8080 already in use (hung dashboard process)

```bash
pkill -f "app.py"
sleep 1
curl -I http://localhost:8080
```

### Waypoint buttons dead / waypoint JS rendered as HTML

The `&lt;/script&gt;` tag was closed before the waypoint JS. All dashboard
JS must live inside the single `&lt;script&gt;...&lt;/script&gt;` block. If the
page regressed, restore from git (see above).

### Waypoint follower ignores obstacle

E-stop integration added 14 Oct. Verify both nodes are running:

```bash
ros2 node list | grep ultrasonic
ros2 topic echo /emergency_stop
```

---

## 16. Ultrasonic Emergency Stop (HC-SR04)

*Status (14 Oct): DONE. 2× front HC-SR04 sensors angled inward for center
coverage. /emergency_stop = True when obstacle &lt;30 cm. Waypoint follower
halts autonomous run on trigger.*

### Wiring

| Sensor | Trig GPIO | Echo GPIO | Note |
|--------|-----------|-----------|------|
| Left | GPIO17 (Pin 11) | GPIO22 (Pin 15) | Echo via 1kΩ + 2kΩ voltage divider |
| Right | GPIO23 (Pin 16) | GPIO27 (Pin 13) | Echo via 1kΩ + 2kΩ voltage divider |

HC-SR04 Echo outputs 5V — the divider (1kΩ series + 2kΩ to GND) scales
it to ~3.3V to protect the Pi inputs. Trig is 3.3V-safe as-is (sensor
triggers at ~2.5V). VCC → 5V red rail, GND → blue rail.

### Run + verify

```bash
ros2 run robot_control ultrasonic_node
ros2 topic echo /ultrasonic/front    # live distance in metres (min of both)
ros2 topic echo /emergency_stop      # True when &lt;30 cm

# Wave a hand in front of either sensor → /emergency_stop flips True
```

### Safety chain

```
HC-SR04 × 2 → ultrasonic_node → /ultrasonic/front (Float32, metres)
                              → /emergency_stop (Bool, &lt;30 cm)
                                    ↓
              waypoint_follower: running=False, zero /cmd_vel,
              logs "EMERGENCY STOP — obstacle detected!"
```

Manual drive (keyboard/pad) is unaffected — the E-stop halts only the
autonomous run. Any future sensor (bump switch, IR) can publish to the
same `/emergency_stop` topic to join the chain.

---

## 17. robot_localization EKF

*Status (12 Oct): DONE. Fuses /odom (encoders) + /imu/data (BNO055) →
/odometry/filtered at 20 Hz. two_d_mode: true, world_frame: odom.*

### Install

```bash
sudo apt install ros-jazzy-robot-localization -y
```

### EKF config (config/ekf.yaml)

```yaml
ekf_filter_node:
  ros__parameters:
    frequency: 20.0
    sensor_timeout: 0.1
    two_d_mode: true
    publish_tf: true
    world_frame: odom

    odom0: /odom
    odom0_config: [true, true, false,
                   false, false, false,
                   true, false, false,
                   false, false, true,
                   false, false, false]
    odom0_queue_size: 10
    odom0_differential: false

    imu0: /imu/data
    imu0_config: [false, false, false,
                  false, false, true,
                  false, false, false,
                  false, false, true,
                  false, false, false]
    imu0_differential: true
    imu0_queue_size: 10
    imu0_remove_gravitational_acceleration: true
```

### Run the EKF

```bash
# Via bringup (recommended):
ros2 launch robot_control bringup.launch.py

# Or manually:
ros2 run robot_localization ekf_node --ros-args --params-file ~/ros2_ws/src/robot_control/config/ekf.yaml
```

### Verify EKF output

```bash
ros2 topic hz /odometry/filtered
ros2 topic echo /odometry/filtered
# Expected: ~20 Hz, position tracks real robot motion
```

### Known drift

Without GPS loop closure, the EKF drifts ~0.8 m per metre of hand-pushed
travel. Expected for dead-reckoning indoors. Short waypoint legs (&lt;2 m)
are accurate enough for the demo; GPS corrects drift outdoors via
navsat_transform_node (already in the launch file, standby).

---

## 18. Indoor Waypoint Navigation (waypoint_follower)

*Status (12–14 Oct): DONE. Proportional control indoor navigation with
emergency stop integration. 15 cm position tolerance, 0.15 rad
orientation tolerance.*

### How it works

```
Dashboard buttons → /waypoint/save, /waypoint/clear, /waypoint/run, /waypoint/stop
ultrasonic_node   → /emergency_stop (halts run)
    ↓
waypoint_follower → subscribes /odometry/filtered (EKF pose)
                  → publishes /cmd_vel (only when running)
                  → saves/loads waypoints from waypoints.json
```

### Control logic

| Condition | Action |
|-----------|--------|
| `/emergency_stop` = True | Halt: running=False, zero /cmd_vel |
| `|yaw_err| &gt; 0.5 rad` | Turn in place at `±0.3 rad/s` |
| `|yaw_err| &lt;= 0.5 rad` | Drive forward at `0.15 * dist` capped at `0.15 m/s` |
| `dist &lt; 0.15 m` | Waypoint reached → next waypoint or stop |

### Run

```bash
# Via bringup (EKF + follower + ultrasonic start together):
ros2 launch robot_control bringup.launch.py
```

Dashboard workflow:
1. **Save Waypoint** — captures current `{x, y, yaw}` from EKF
2. **Run** — robot turns toward first waypoint, drives forward
3. **Stop** — halts autonomous mode, returns to manual control
4. **Clear All** — deletes all saved waypoints

### Verify

```bash
ros2 topic hz /odometry/filtered     # EKF feeding the follower
ros2 topic hz /cmd_vel               # publishing during Run
cat ~/ros2_ws/src/robot_control/waypoints.json
```

### Manual drive during autonomous mode

The dashboard `autonomous` flag prevents it from publishing `/cmd_vel`
when the waypoint follower is running. Press **Stop** to return to
manual control (keyboard or drive pad).

### Tuning

If the robot overshoots or oscillates, edit `waypoint_follower.py`:

```python
ANGULAR_MAX = 0.3       # rad/s
LINEAR_MAX = 0.15       # m/s
YAW_THRESHOLD = 0.5     # rad (turn-in-place threshold)
POS_TOLERANCE = 0.15    # m
ORIENTATION_TOLERANCE = 0.15   # rad
```

---

## 19. Project File Locations on Pi

| File / Folder | Path on Raspberry Pi |
|---------------|----------------------|
| Camera stream node | ~/ros2_ws/src/robot_control/robot_control/camera_stream.py |
| Capture node | ~/ros2_ws/src/robot_control/robot_control/capture.py |
| AI inference node | ~/ros2_ws/src/robot_control/robot_control/ai_inference.py |
| Motor driver node | ~/ros2_ws/src/robot_control/robot_control/motor_driver.py |
| Encoder node | ~/ros2_ws/src/robot_control/robot_control/encoder_node.py |
| IMU node | ~/ros2_ws/src/robot_control/robot_control/imu_node.py |
| GPS node | ~/ros2_ws/src/robot_control/robot_control/gps_node.py |
| Env sensor node | ~/ros2_ws/src/robot_control/robot_control/env_node.py |
| Ultrasonic node | ~/ros2_ws/src/robot_control/robot_control/ultrasonic_node.py |
| Waypoint follower | ~/ros2_ws/src/robot_control/robot_control/waypoint_follower.py |
| Bringup launch file | ~/ros2_ws/src/robot_control/launch/bringup.launch.py |
| EKF config | ~/ros2_ws/src/robot_control/config/ekf.yaml |
| Waypoints file | ~/ros2_ws/src/robot_control/waypoints.json |
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

## 20. Status Snapshot (14 Oct 2026)

| Area | Status |
|------|--------|
| Camera + streaming | Done — USB webcam, stream + capture nodes working |
| AI model (train → TFLite → Pi inference) | Done — 90.1% val accuracy, 3.5 ms/frame on Pi CPU |
| Background class + confidence threshold | Done — retrained with Other class |
| Domain gap fix (webcam leaf shots) | Done — sorted into class folders |
| Farmer dashboard | Done — Mission Control unified page live |
| Motors (4-wheel drivetrain) | Done — all 4 wheels, forward + turn verified |
| Web drive control | Done — embedded in dashboard + standalone /control |
| One-command bringup | Done — 9 nodes + rosbridge + camera stream |
| Encoder odometry (4-wheel, signed, TF) | Done 7 Oct — zero drift, ~90 ticks/m |
| IMU (BNO055 I2C fusion) | Done 8 Oct — /imu/data at 20 Hz |
| GPS (NEO-8M UART /fix) | Done 8 Oct — publishing always; fix needs sky view |
| Environmental sensor (AHT30) | Done 9 Oct — /env/temperature + /env/humidity |
| robot_localization EKF | Done 12 Oct — /odometry/filtered at 20 Hz |
| Indoor waypoint navigation | Done 12 Oct — proportional follower, 15 cm tolerance |
| Ultrasonic emergency stop | **Done 14 Oct** — 2× HC-SR04, /emergency_stop &lt;30 cm, follower halts |
| Indoor stack | **COMPLETE** — one bringup launch, verified end-to-end |
| AI scan at each waypoint | Not started |
| Battery monitor (ADS1115) | Not started (when LiPo returns) |
| Battery | Done — 11.1V 3S 45C 5500mAh LiPo purchased |
| Report + viva | 25 Nov / 30 Nov / 2 Dec 2026 |
