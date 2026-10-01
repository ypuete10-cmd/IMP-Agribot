# Pi 5 Command Reference

*Updated: 22 Sep 2026 — adds AI inference node (TFLite on Pi CPU), model training pipeline (Windows laptop), ai-edge-litert deployment notes*

Replace `[PI_IP]` with the actual Pi IP address (usually 10.251.117.169 on the current network). The IP changes when you switch networks.

## 1. SSH Access to Raspberry Pi 5

From Windows PowerShell (not WSL):

```bash
ssh yvette_pi@[PI_IP]
```

If SSH fails, the IP may have changed. Check on the Pi monitor:

```bash
ip addr show | grep "inet 10"
```

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

&gt; Note: The farmer dashboard (Section 9) does NOT need colcon build — run its scripts directly with python3. It is not a ROS2 package.

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

&gt; Note: Only one node can hold the camera at a time. If camera_stream or ai_inference is running, kill it before opening the camera elsewhere.

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

Behavior notes: results below 0.60 confidence are published as `unknown_no_plant` (safety net). The "Other" class covers walls/desks — trained on 800 negatives + 30 real webcam background shots. Domain gap fix (webcam leaf shots) in progress as of 22 Sep.

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

Expected training results so far: 15-class model 89.9% val accuracy; 16-class (with Other) 89.8% val accuracy. Lab-image test: Tomato___Late_blight 89.3% / 87.5%.

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
```

### Check disk space

```bash
df -h
```

### Check battery voltage (if ADS1115 wired)

```bash
python3 ~/battery_monitor.py
```

## 8. Running ROS2 Nodes

Open a separate terminal (SSH window) for each node.

```bash
# Terminal 1 — Camera stream (port 5000)
ros2 run robot_control camera_stream

# Terminal 2 — AI inference (publishes /plant_health)
ros2 run robot_control ai_inference

# Terminal 3 — Motor driver (bring-up pending)
ros2 run robot_control motor_driver

# Terminal 4 — Monitor
ros2 topic list
ros2 topic echo /plant_health
ros2 topic echo /cmd_vel
```

&gt; Note: camera_stream and ai_inference both want the webcam — run only one at a time for now (later: ai_inference subscribes to /camera/image_raw instead).

## 9. Farmer Dashboard (Farmer-Facing UI)

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

result_logger currently SIMULATES one waypoint scan every 10 s. In Week 6, `simulate_scan()` gets replaced with real GPS + classifier subscriptions.

### View on laptop

```
http://[PI_IP]:8080
```

- Port 8080 = dashboard. Port 5000 = camera stream. Do not mix them up.
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

## 10. GPS (NEO-8M GNSS) Setup

### Enable UART on Pi 5

```bash
sudo nano /boot/firmware/config.txt
# Add at the bottom:
enable_uart=1
# Then: sudo reboot
```

### Test GPS raw data

```bash
minicom -b 9600 -o -D /dev/ttyAMA0
```

You should see NMEA sentences ($GNGGA, $GNRMC). Ctrl+A then X to quit. *(Not yet wired as of 22 Sep.)*

### Run GPS ROS2 node (after wiring)

```bash
ros2 run nmea_navsat_driver nmea_serial_driver --ros-args -p port:=/dev/serial0 -p baud:=9600
```

## 11. Git Backup to GitHub

Repo is at `~/ros2_ws/src/robot_control` and is pushed regularly. Configure once:

```bash
git config --global user.name "Yvette Lee"
git config --global user.email "your-email@example.com"
```

### Commit and push (run on Pi after changes)

```bash
cd ~/ros2_ws/src/robot_control
git add .
git commit -m "description of changes"
git push origin main
```

Use a Personal Access Token (not your GitHub password) when prompted. Also commit training scripts and the model:

```bash
mkdir -p ~/ros2_ws/src/robot_control/{training,models}
cp ~/*.py ~/ros2_ws/src/robot_control/training/
cp ~/plant_health.tflite ~/class_names.json ~/ros2_ws/src/robot_control/models/
```

## 12. Quick Fixes

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

## 13. Project File Locations on Pi

| File / Folder | Path on Raspberry Pi |
|---------------|----------------------|
| Camera stream node | ~/ros2_ws/src/robot_control/robot_control/camera_stream.py |
| Capture node | ~/ros2_ws/src/robot_control/robot_control/capture.py |
| AI inference node | ~/ros2_ws/src/robot_control/robot_control/ai_inference.py |
| Motor driver node | ~/ros2_ws/src/robot_control/robot_control/motor_driver.py |
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

## 14. Status Snapshot (22 Sep 2026)

| Area | Status |
|------|--------|
| Camera + streaming | Done — USB webcam, stream + capture nodes working |
| AI model (train → TFLite → Pi inference) | Done — 85% val accuracy, 3.5 ms/frame on Pi CPU |
| Background class + confidence threshold | Done — retrained with Other class |
| Domain gap fix (webcam leaf shots) | IN PROGRESS — capture + retrain tonight |
| Farmer dashboard | Done — simulated scans; real GPS+AI hookup in Week 6 |
| Motors (L298N bring-up) | Not started — next critical task |
| GPS / IMU / encoders wiring | Not started |
| nav2 + EKF navigation | Not started |
| Report + viva | 2 Dec 2026 |
