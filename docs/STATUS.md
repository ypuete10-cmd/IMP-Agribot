# Project Status

**Yvette Lee EnQi (25034155)** — Autonomous Agricultural Robot for Crop Health Monitoring
Last updated: 12 November 2026 · Viva: 2 December 2026

---

## Repo Structure

```
robot_control/
├── robot_control/
│   ├── motor_driver.py          # PWM diff-drive + e-stop + watchdog latch + min_pwm=0.25
│   ├── camera_stream.py         # Flask MJPEG stream (port 5000) + frame sharing
│   ├── capture.py               # Single photo capture
│   ├── ai_inference.py          # Event-driven TFLite scanner + manual scan + normalization fix (waypoint-triggered)
│   ├── encoder_node.py          # 4-wheel encoders + odometry + TF
│   ├── imu_node.py              # BNO055 I2C IMU, publishes /imu/data
│   ├── gps_node.py              # NEO-8M UART GPS, publishes /fix
│   ├── env_node.py              # AHT30 I2C temp/humidity, publishes /env/*
│   ├── waypoint_follower.py     # Indoor autonomous nav, pause-resume + scan handshake
│   └── ultrasonic_node.py       # 2× HC-SR04 front sensors, debounced emergency stop
├── launch/
│   └── bringup.launch.py        # 10-process one-command bringup
├── config/
│   └── ekf.yaml                 # robot_localization EKF config (frequency: 5.0)
├── dashboard/                   # Mission Control (Flask, port 8080)
│   ├── app.py                   # Server + camera proxy
│   ├── result_logger.py
│   ├── data/results.json
│   ├── templates/index.html     # Mission Control page
│   └── drive/control.html       # Standalone drive page
├── models/                      # plant_health.tflite + class_names.json
├── training/                    # PlantVillage training pipeline scripts
└── docs/                        # Build log, status, command reference, figures
```

## What Works Now

1. SSH access from Windows PowerShell; workspace builds with colcon
2. Camera live stream (port 5000) and photo capture via ROS2 node
3. **AI inference on-device** — 16-class MobileNetV3-Small, TFLite float16,
   90.1% val accuracy, 3.5 ms/frame (282 FPS) on Pi 5 CPU; /plant_health
   topic verified end-to-end with confidence threshold (0.60 → unknown_no_plant)
4. **AI-waypoint integration (v3)** — event-driven scanner: `ai_inference`
   subscribes `/waypoint/reached`, grabs shared frame from `/tmp/latest_frame.jpg`,
   classifies, logs to `results.json` (atomic write), publishes `/plant_health`
   + `/waypoint/scan_done`. Waypoint follower freezes during scan, auto-resumes
   to next waypoint after `scan_done`.
5. **Mission Control dashboard** (port 8080) — unified page with live sensor
   cards (GPS, odom, heading, env, AI scan), embedded camera + drive pad,
   keyboard WASD/arrow control, waypoint Save/Run/Stop buttons, GPS map,
   results table. All data via rosbridge WebSocket. Camera proxy with zero
   hardcoded IPs. Throttle rates on `/imu/data` (10 Hz) and `/odom` (4 Hz)
   to prevent rosbridge queue overflow.
6. **4-wheel drive teleop** — dual L298N via breadboard signal sharing;
   forward and turn-in-place verified with keyboard teleop and web drive pad
7. **One-command bringup** — `ros2 launch robot_control bringup.launch.py`
   starts 10 processes: motor, encoder, IMU, env, GPS, EKF, waypoint follower,
   ultrasonic, **ai_inference**, rosbridge, and camera stream
8. **Web drive control** — embedded in Mission Control + standalone at
   `/control` (WASD/arrow keys, speed slider, auto-stop, no hardcoded IP)
9. **Encoder odometry** — 4× LM393 encoders wired (GPIO 5/6/13/19), publishes
   /wheel_ticks + /odom + odom→base_link TF; calibrated ~90 ticks/m,
   ±10% per-leg accuracy, zero drift at rest
10. **BNO055 IMU** — I2C @0x29, NDOF mode, publishes /imu/data at 20 Hz
    (quaternion + gyro + accel). Onboard fusion; no Madgwick needed.
11. **NEO-8M GPS** — UART /dev/ttyAMA0 @9600, publishes /fix at 1 Hz
    always (status -1 when no fix). Stream verified; position fix needs sky view.
12. **AHT30 environmental sensor** — I2C (shares bus with BNO055), publishes
    /env/temperature and /env/humidity
13. **robot_localization EKF** — fuses /odom + /imu/data → /odometry/filtered
    at 5 Hz (two_d_mode, world_frame: odom). Encoder covariances added.
    Frequency reduced from 20→5 to prevent "Failed to meet update rate" on Pi 5.
14. **Indoor waypoint navigation** — waypoint_follower node: Save waypoints
    from EKF pose, Run to autonomously navigate with proportional control
    (turn-in-place threshold 0.8 rad, 15 cm tolerance, lin=0.3 max).
    Manual drive resumes after Stop via autonomous flag.
15. **Ultrasonic emergency stop v2** — 2× HC-SR04 front sensors (Trig GPIO17/23,
    Echo GPIO22/27 with voltage dividers). Motor-level cut-off: motor_driver
    zeroes both motors on `/emergency_stop`. Waypoint follower pause-resume:
    freezes on obstacle, auto-resumes when clear. Noise filtering: staggered
    pings (+20ms), median-of-3 sampling, 5-reading debounce, 2cm glitch filter.
    Threshold: 10cm (indoor), configurable via `THRESHOLD_CM`.
16. **QoS fix** — Explicit `QoSProfile(RELIABLE, VOLATILE, KEEP_LAST/10)`
    on `/cmd_vel` publisher (waypoint_follower) and subscriber (motor_driver).
    Fixed silent message dropping due to TRANSIENT_LOCAL / VOLATILE mismatch.
17. **Motor driver watchdog latch** — `watchdog_callback()` now uses
    `self.watchdog_triggered` flag. Only stops motors ONCE on timeout,
    resets when new `/cmd_vel` arrives. Fixed robot refusing to move after
    manual drive stops.
18. **End-to-end autonomous mission** — **VERIFIED:** Run → Drive → Arrive →
    Scan → Resume → Complete. 1 m navigation accurate to ~5 cm. Emergency
    stop pauses and resumes correctly.
19. **Manual AI Scan Mode** — Drive robot manually to any location, click
    **"Scan Plant"** on dashboard to trigger on-demand classification. Result
    logged as "WP-00" with live status indicator ("Scanning..." → "Done").
    No waypoint setup required.
20. **AI normalization fix** — MobileNetV3 preprocessing corrected from raw
    uint8 `[0, 255]` to normalized `[-1, 1]` (`img / 127.5 - 1.0`). Added
    class-probability debug logging for accuracy tuning.
21. **Motor PWM floor fix (10 Nov)** — `min_pwm` reduced from 0.4 → **0.25**.
    Previous 0.4 forced every nonzero motor command to ≥40% duty, causing
    overshoot, oscillation, and asymmetric arcs during turns. EKF was correct —
    the robot physically moved 4–7× faster than commanded.
22. **EKF IMU yaw fusion fix (10 Nov)** — `ekf.yaml` changed: IMU absolute yaw
    (magnetometer-derived, corrupted by motor-wire magnetic interference)
    **disabled**. Encoders now own yaw (self-consistent with position); IMU
    contributes yaw rate only. Fixed robot driving away from waypoint while
    `yaw_err ≈ 0`.
23. **Ultrasonic 5V power fix (10 Nov)** — HC-SR04 VCC moved from 3.3V rail to
    **Pi 5V Pin 2** (echo dividers retained). Previous 3.3V supply starved the
    transmitter → weeks of phantom obstacles and garbage readings. Added
    `>3.0 m` artifact filter to kill timeout-boundary junk (`804 cm`).
24. **Dashboard v2 rewrite (10 Nov)** — Full `index.html` rewrite: Nav Debug
    card (live pos, yaw, dist, yaw_err), live waypoint count via `/api/waypoints`,
    Scan Plant + Clear Log buttons, throttled subscriptions (IMU 10Hz, odom 4Hz,
    env 2Hz) to stop rosbridge queue overflow.
25. **Diagnostic tooling (10 Nov)** — `yaw_check.py` (odom vs filtered yaw),
    `test_ultrasonic.py` (standalone HC-SR04 tester), follower 10Hz WP/CMD
    debug logging.
26. **AI model root cause identified (12 Nov)** — Original model degenerate
    (undertrained/broken at export). Ruled out preprocessing, label
    permutation, and camera issues via systematic testing. Retraining confirmed
    as only correct fix.
27. **AI model retrained (12 Nov)** — MobileNetV3Small transfer learning on
    FULL dataset via RTX 5050/WSL2. **95.1% validation accuracy**, 5/5 sanity
    checks passed. `class_names.json` exported from `train_ds.class_names` in
    same script → label misalignment structurally impossible.
28. **Viva terminology locked (12 Nov)** — Single-label image classifier
    (not YOLO/object detection). Station-based inspection presented as
    deliberate design. Examiner Q&A prepared for detection-vs-classification
    question.

## What Is Left (Priority Order)

| # | Task | Due |
|---|------|-----|
| 1 | Deploy new AI model to Pi (scp + backup + reboot) | Nov |
| 2 | 8-print score test (expect 7–8/8) | Nov |
| 3 | Straight run + box test with new EKF + min_pwm 0.25 | Nov |
| 4 | Multi-waypoint mission (2+ waypoints with scan at each) | Nov |
| 5 | Camera lag reduction (640×480 @ 15 fps) | Nov |
| 6 | Remove debug logging (reduce log spam) | Nov |
| 7 | Tune arrival tolerance (15cm → 20cm if needed) | Nov |
| 8 | Field-test waypoint accuracy on actual floor | Nov |
| 9 | ADS1115 battery monitor (when LiPo returns) | Nov |
| 10 | Report writing + documentation | Nov–Dec |
| 11 | Viva presentation slides | 30 Nov |
| 12 | Final demo / viva | **2 Dec 2026** |

## Hardware Status

| Component | Status | Notes |
|-----------|--------|-------|
| Raspberry Pi 5 + Ubuntu 24.04 | Working | ROS2 Jazzy, 8 GB RAM |
| USB Webcam (1080p) | Working | V4L2/UVC, replaces Pi Camera v2 |
| Dual L298N + 4× TT motors | Working | Breadboard signal sharing |
| 4× LM393 encoders | Working | GPIO 5/6/13/19, ~90 ticks/m |
| BNO055 IMU | Working | I2C @0x29, NDOF mode, onboard fusion |
| NEO-8M GPS | Working | UART /dev/ttyAMA0, 1 Hz, needs sky view |
| AHT30 temp/humidity | Working | Shares I2C bus with BNO055 |
| 2× HC-SR04 ultrasonic | Working | Trig 17/23, Echo 22/27, 10cm threshold |
| 3S LiPo 11.1V 5500mAh | Borrowed | ~3.5 h runtime; return by 4 Dec |
| HW-688 buck converter | Working | 12V→5V logic power |
| ADS1115 battery monitor | Pending | When LiPo returns |
| Front bumper / protective guard | Not built | Optional for outdoor demo |

## GPIO Pinout (BCM, Final)

| GPIO | Function | Pin # |
|------|----------|-------|
| 12 | ENA (PWM, left motors) | 32 |
| 16 | IN1 (left forward) | 36 |
| 20 | IN2 (left reverse) | 38 |
| 18 | ENB (PWM, right motors) | 12 |
| 25 | IN3 (right forward) | 22 |
| 26 | IN4 (right reverse) | 37 |
| 5 | Encoder FL (D0) | 29 |
| 6 | Encoder FR (D0) | 31 |
| 13 | Encoder RL (D0) | 33 |
| 19 | Encoder RR (D0) | 35 |
| 2 | SDA (I2C) | 3 |
| 3 | SCL (I2C) | 5 |
| 14 | UART TX | 8 |
| 15 | UART RX | 10 |
| 17 | HC-SR04 Trig #1 | 11 |
| 23 | HC-SR04 Trig #2 | 16 |
| 22 | HC-SR04 Echo #1 (with divider) | 15 |
| 27 | HC-SR04 Echo #2 (with divider) | 13 |

**Spare GPIO:** 4, 7, 8, 9, 10, 11, 21, 24

## Topic Map

| Topic | Type | Publisher | Subscriber(s) |
|-------|------|-----------|---------------|
| /cmd_vel | Twist | dashboard, waypoint_follower, teleop | motor_driver |
| /wheel_ticks | Int32MultiArray | encoder_node | — |
| /odom | Odometry | encoder_node | ekf_filter_node, dashboard |
| /imu/data | Imu | imu_node | ekf_filter_node, dashboard |
| /odometry/filtered | Odometry | ekf_filter_node | waypoint_follower, dashboard |
| /fix | NavSatFix | gps_node | dashboard, navsat_transform_node |
| /env/temperature | Temperature | env_node | dashboard |
| /env/humidity | RelativeHumidity | env_node | dashboard |
| /plant_health | String (JSON) | ai_inference | dashboard |
| /ultrasonic/front | Float32 | ultrasonic_node | — |
| /emergency_stop | Bool | ultrasonic_node | motor_driver, waypoint_follower |
| /waypoint/save | Empty | dashboard | waypoint_follower |
| /waypoint/clear | Empty | dashboard | waypoint_follower |
| /waypoint/run | Empty | dashboard | waypoint_follower |
| /waypoint/stop | Empty | dashboard | waypoint_follower |
| /waypoint/reached | Float32MultiArray | waypoint_follower | ai_inference |
| /waypoint/scan_done | Empty | ai_inference | waypoint_follower |
| /ai/scan_trigger | Empty | dashboard | ai_inference |

## Known Issues

1. **Debug logging is verbose** — real-time WP/CMD logs and watchdog state
   spam the terminal. Remove or reduce before demo day.
2. **Camera lag** — 1080p @ 30 fps may overload Pi CPU. Next: drop to
   640×480 @ 15 fps + JPEG quality 70 in `camera_stream.py`.
3. **Encoder drift** — ±10% per-leg without GPS loop closure. Documented
   limitation; EKF helps but does not eliminate accumulated drift.
4. **IMU tilt** — BNO055 mounted ~18° off horizontal. Must remount flat
   before outdoor nav2 demo.
5. **GPS no fix indoors** — expected; status -1 with 0.0/0.0. Needs sky
   view for position lock. Navsat transform node ready for outdoor use.
6. **LCD moiré** — leaf images on phone screens misclassify occasionally.
   Use printed photos or real leaves for demo.
7. **Arrival tolerance** — currently 15 cm; may need 20 cm for reliability
   on actual floor surfaces.
8. **Camera proxy ChunkedEncodingError** — restarting bringup breaks Flask
   camera stream. Fix: restart dashboard + browser refresh after bringup.
9. **Turning power on carpet** — may need PWM increase for carpet surfaces.
   Current values tuned for smooth lab floor.
10. **Soft-object ultrasonic detection** — bags/fabric absorb ultrasound.
    This is a physics limitation of HC-SR04, not a wiring issue. Solid
    obstacles (walls, boxes) detected reliably after 5V power fix.
11. **PlantVillage domain gap** — prints/photos-of-photos degrade AI accuracy.
    Screen-displayed dataset images expected to classify correctly.
    **Mitigated (12 Nov):** New model retrained at 95.1% val; 8-print test
    pending to quantify print-quality impact.
12. **Encoder drift at standstill** — minor drift during long obstacle holds.
    Mitigated by short holds; documented limitation for report.
13. **Old AI model degenerate** — original model undertrained/broken at export,
    never verified with real images. **FIXED (12 Nov):** Replaced with
    MobileNetV3Small transfer learning (95.1% val, RTX 5050/WSL2).

## Critical Path

```
[COMPLETED] Chassis → AI pipeline → Electronics → 4WD → Web drive
[COMPLETED] Bringup launch → Encoders → Sensors → Dashboard
[COMPLETED] EKF → Waypoint nav → Ultrasonic v1 → Ultrasonic v2
[COMPLETED] AI-waypoint integration (event-driven scanner + scan handshake)
[COMPLETED] Working autonomous navigation + AI scan (29 Oct 2026)
[COMPLETED] Manual AI Scan mode + normalization fix (2 Nov 2026)
[COMPLETED] Three root causes fixed: min_pwm 0.25, EKF IMU-yaw removal, ultrasonic 5V (10 Nov 2026)
[COMPLETED] AI model root cause identified + retrained at 95.1% val (12 Nov 2026)
[ACTIVE]    Deploy new model → 8-print test → straight run + box test
[UPCOMING]  Multi-waypoint mission → Camera lag fix → Field test → Report → Slides → Viva (2 Dec 2026)
```

## Quick Commands

```bash
# Build workspace
cd ~/ros2_ws && colcon build --symlink-install && source install/setup.bash

# One-command bringup (10 processes)
ros2 launch robot_control bringup.launch.py

# Dashboard (second terminal)
python3 ~/ros2_ws/src/robot_control/dashboard/app.py

# Monitor emergency stop
ros2 topic echo /emergency_stop

# Monitor ultrasonic distance
ros2 topic echo /ultrasonic/front

# Verify /cmd_vel is flowing during Run
ros2 topic echo /cmd_vel --once
timeout 3 ros2 topic hz /cmd_vel

# Verify all nodes running
ros2 node list

# Check QoS compatibility
ros2 topic info /cmd_vel --verbose

# Monitor waypoint scan handshake
ros2 topic echo /waypoint/reached
ros2 topic echo /waypoint/scan_done

# Trigger manual AI scan (from terminal)
ros2 topic pub /ai/scan_trigger std_msgs/msg/Empty {}

# Monitor AI classification results
ros2 topic echo /plant_health
```

## File Locations

| File | Path |
|------|------|
| Workspace | `~/ros2_ws/` |
| Package source | `~/ros2_ws/src/robot_control/` |
| Bringup launch | `~/ros2_ws/src/robot_control/launch/bringup.launch.py` |
| EKF config | `~/ros2_ws/src/robot_control/config/ekf.yaml` |
| Motor driver | `~/ros2_ws/src/robot_control/robot_control/motor_driver.py` |
| Encoder node | `~/ros2_ws/src/robot_control/robot_control/encoder_node.py` |
| IMU node | `~/ros2_ws/src/robot_control/robot_control/imu_node.py` |
| GPS node | `~/ros2_ws/src/robot_control/robot_control/gps_node.py` |
| Env node | `~/ros2_ws/src/robot_control/robot_control/env_node.py` |
| Waypoint follower | `~/ros2_ws/src/robot_control/robot_control/waypoint_follower.py` |
| Ultrasonic node | `~/ros2_ws/src/robot_control/robot_control/ultrasonic_node.py` |
| AI inference | `~/ros2_ws/src/robot_control/robot_control/ai_inference.py` |
| Camera stream | `~/ros2_ws/src/robot_control/robot_control/camera_stream.py` |
| Dashboard app | `~/ros2_ws/src/robot_control/dashboard/app.py` |
| Dashboard HTML | `~/ros2_ws/src/robot_control/dashboard/templates/index.html` |
| Drive page | `~/ros2_ws/src/robot_control/dashboard/drive/control.html` |
| AI model | `~/ros2_ws/src/robot_control/models/plant_health.tflite` |
| Waypoint JSON | `~/ros2_ws/src/robot_control/waypoints.json` |
| Results log | `~/ros2_ws/src/robot_control/dashboard/data/results.json` |
| Shared frame | `/tmp/latest_frame.jpg` |
| Build log | `docs/BUILD_LOG.md` |
| Command reference | `docs/COMMAND_REFERENCE.md` |

---

*Yvette Lee EnQi (25034155) — Graduation Project, 2026*
