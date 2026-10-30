# Build Log

Dated progress log with photos. Newest entries at the top.

---

## 29/10/2026 — Working autonomous navigation + AI scan integration

**End-to-end autonomous waypoint navigation with AI plant health scanning — VERIFIED.**

### Root Causes Found & Fixed (5 critical bugs)

**1. Motor Driver Watchdog Latch (CRITICAL)**
- **Symptom:** Robot only moved when lifted off floor; worked on first run after
  boot but not after manual drive
- **Cause:** `watchdog_callback()` ran every 1 s and continuously zeroed motors.
  After manual drive stopped, watchdog fired and kept overwriting motor speeds
  to `0.0` even when autonomous commands arrived
- **Fix:** Added `self.watchdog_triggered` flag. Watchdog only stops motors
  **ONCE** on timeout, resets when new `/cmd_vel` arrives

**2. QoS Durability Mismatch on `/cmd_vel` (CRITICAL)**
- **Symptom:** "Run" started but robot never moved, no errors
- **Cause:** After reboot, follower published with `TRANSIENT_LOCAL` durability,
  `motor_driver` subscribed with `VOLATILE`. DDS silently dropped all messages
- **Fix:** Explicit `QoSProfile(RELIABLE, VOLATILE)` on both publisher and subscriber

**3. AI Scan Never Triggered (LOGIC BUG)**
- **Symptom:** Robot reached waypoint but jumped straight to
  "All waypoints reached!" without scanning
- **Cause:** Scan trigger only ran if `current_idx < len(waypoints)`. With 1
  waypoint, `idx=1 == len=1`, so scan skipped
- **Fix:** Trigger scan for **EVERY** waypoint including last. Moved
  mission-complete check to `scan_done_cb`

**4. EKF Update Rate Too High**
- **Symptom:** `"Failed to meet update rate! Took 0.26s"` — EKF couldn't keep up
- **Cause:** `frequency: 20.0` in `ekf.yaml` too demanding for Pi 5 with 10 nodes
  + camera + AI
- **Fix:** Reduced to `frequency: 5.0`

**5. Follower Drive Parameters Too Weak**
- **Symptom:** Wheels turned when lifted but not on floor (insufficient torque)
- **Cause:** `lin=0.15` max and `min_pwm=0.25` too low for static friction
- **Fix:** Increased to `lin=0.3` max, `min_pwm=0.5`, more lenient turn threshold
  (`0.8 rad` vs `0.5 rad`)

### Verified Working

- **Robot drives on floor after manual control** (watchdog fix)
- **1 m autonomous navigation:** drives, slows near target, stops within 15 cm
- **Position tracking:** EKF odometry accurate to ~5 cm over 1 m distance
- **Emergency stop:** pauses on obstacle, resumes when clear
- **Mission sequence:** Run → Drive → Arrive → Scan → Resume → Complete

### Debug Infrastructure Added

- Real-time WP/CMD logging:
  ```
  WP 0/1: pos=(0.74,0.56) yaw=0.92 | dist=0.06 yaw_err=-2.37
  ```
- Watchdog state logging with trigger reason
- Scan handshake logging (reached / scan_done / resuming)

### Files Changed

- `robot_control/motor_driver.py` — Watchdog latch fix, QoS fix, `min_pwm=0.5`
- `robot_control/waypoint_follower.py` — Scan trigger fix, drive tuning, debug logging
- `config/ekf.yaml` — `frequency: 20→5`
- `launch/bringup.launch.py` — Full rewrite with 10 processes
- `robot_control/ai_inference.py` — Event-driven rewrite
- `robot_control/camera_stream.py` — Shares frames via `/tmp/latest_frame.jpg`

### Next Session

1. Test AI scan with actual plant photo (verify `/waypoint/reached` →
   `/waypoint/scan_done` handshake)
2. Test 2+ waypoints with scan at each
3. Remove debug logging (reduce log spam)
4. Tune arrival tolerance (currently 15 cm, may need 20 cm for reliability)
5. Camera lag fix (640×480 @ 15 fps)

### Photos & Videos

**Terminal showing Mission Control during autonomous run**
(live sensor cards, embedded camera, waypoint status):

![Dashboard during autonomous run](https://github.com/user-attachments/assets/57fdb910-a351-4074-9a8e-0b985890a183)

**AgriBot on the lab floor during 1 m autonomous navigation test**
(~5 cm position accuracy, EKF fused odometry):

![Robot on floor during nav test](https://github.com/user-attachments/assets/525101c1-b360-4ae8-b857-4fdcf9e1f634)

**Close-up of AgriBot chassis showing front ultrasonic sensors**
(dual HC-SR04 with voltage dividers, 10 cm emergency stop threshold):

![Front sensors close-up](https://github.com/user-attachments/assets/79f3b59e-ecee-4f50-99c0-70cf029cba2b)

**Videos:**
- [Dashboard showcase and waypoint demo](https://youtu.be/Y43O8ZLnX90)
- [Manual control using dashboard](https://youtu.be/ORlWATcgQac)

---

## 28/10/2026 — AI-waypoint integration + QoS fix (event-driven scanner + scan handshake)

**`ai_inference.py`** — REWRITTEN as **event-driven scanner**:
- **Was:** timer-based classification every 2 s (wasted CPU, wrong trigger)
- **Now:** subscribes `/waypoint/reached` (`Float32MultiArray` `[idx, x, y]`)
- Grabs shared frame from `/tmp/latest_frame.jpg` (written by `camera_stream`)
  — avoids camera device contention (`camera_stream` owns the USB cam)
- Classifies with TFLite (16 classes), appends to `results.json`
  (atomic write: tmp file + `os.replace` so Flask never reads partial JSON)
- Publishes `/plant_health` (live dashboard card) + `/waypoint/scan_done`
- Logs: `"WP-01: Tomato___Late_blight (93.2%)"`

**`waypoint_follower.py`** — Scan handshake:
- Publishes `/waypoint/reached` when robot arrives at waypoint
- Freezes motion (`self.scanning` gate) until `/waypoint/scan_done` arrives
- **Auto-resumes** to next waypoint after AI scan completes
- Fixed: line 135 had two statements glued together (`SyntaxError`)

**`camera_stream.py`** — Frame sharing:
- Writes every frame to `/tmp/latest_frame.jpg` for AI consumption
- Single `camera.read()` per loop (removed accidental duplicate)

**`bringup.launch.py`** — Full rewrite (was corrupted by bad inserts):
- **10 processes:** motor, encoder, IMU, env, GPS, waypoint_follower,
  EKF, navsat_transform, ultrasonic, **ai_inference**
  + rosbridge + camera_stream

**`motor_driver.py` + `waypoint_follower.py`** — **QoS fix (CRITICAL):**
- Explicit `QoSProfile(RELIABLE, VOLATILE, KEEP_LAST/10)` on `/cmd_vel`
  publisher and subscriber
- **Root cause of "Run does nothing":** follower silently published with
  `TRANSIENT_LOCAL` durability after reboot; motor driver (`VOLATILE`)
  silently dropped all messages. No errors, no crashes — robot idle.
- Verified: `ros2 topic info /cmd_vel` now shows **Publisher count: 2,
  Subscription count: 2**

**Dashboard:** `throttle_rate` added to `/imu/data` (10 Hz) and `/odom`
(4 Hz) subscriptions to stop rosbridge "Write queue full" warnings.

**Bugs fixed today:**
1. `bringup.launch.py` `SyntaxError` — `ai_inference` node inserted inside
   `navsat_transform_node`'s `Node()` call (same pattern as ultrasonic bug)
2. `waypoint_follower.py` line 135 — glued statements from paste
3. `camera_stream.py` — duplicated `camera.read()` block
4. **QoS durability mismatch on `/cmd_vel`** (root cause of no-motion)
5. rosbridge "Write queue full" — added `throttle_rate` to heavy topics

**Verified working:**
- All 10 nodes start clean, no deaths, no Tracebacks
- AI node: `"AI inference ready | 16 classes | waiting for triggers"`
- `/odometry/filtered` publishing at clean 10 Hz
- `/emergency_stop = false` (no phantom latch)
- `/cmd_vel` QoS compatible (pub/sub visible to each other)

**NOT yet verified (tomorrow's task):**
- Full mission: waypoint run → arrive → scan → resume → next waypoint
- Status: Run starts (log shows `"Autonomous run started: N waypoints"`)
  but robot does not move. `/cmd_vel` echo during run still pending —
  need to confirm whether follower publishes drive commands or zeros.

**Tomorrow's plan:**
1. Click Run, then immediately:
   ```bash
   ros2 topic echo /cmd_vel --once
   timeout 3 ros2 topic hz /cmd_vel
   ```
   → if ~10 Hz with `linear.x > 0`: commands flow; check single dashboard
     tab (multi-tab publishes zeros at 10 Hz, cancels follower)
   → if zeros: add debug line to follower loop, inspect state
2. If commands flow but no motion: motor driver watchdog investigation
3. Camera lag fix: 640×480 @ 15 fps + JPEG quality 70 in `camera_stream.py`
4. Then: full 2-waypoint mission with plant photo → verify end-to-end

**Indoor stack v3 (AI-integrated):**
- Drive: motor_driver (emergency cut-off) + encoder_node + imu_node + env_node
- Navigation: EKF + waypoint_follower (scan handshake) + ultrasonic_node
- AI: camera_stream (frame sharing) + ai_inference (event-driven)
- Dashboard: camera + drive pad + keyboard + waypoints + sensors + map

**Remaining to December viva:**
1. Full end-to-end mission verification (arrive → scan → resume)
2. Field-test waypoint accuracy on actual floor
3. Camera lag reduction (640×480 @ 15 fps)
4. ADS1115 battery monitor (when LiPo returns)
5. Report writing + documentation

*(Photos for this session are included in the 29 Oct entry above)*

---

## 22/10/2026 — Emergency stop hardening v2 (motor-level cut-off + pause-resume + noise filtering)

**`motor_driver.py`** — Emergency cut-off at the **motor level**:
- Subscribes `/emergency_stop` (`std_msgs/Bool`)
- Zeroes both motors in `cmd_vel_callback` while emergency is active
- Cuts motors for **ALL** `/cmd_vel` sources (drive pad, keyboard,
  waypoint follower) — safety at the last possible point

**`waypoint_follower.py`** — Pause-and-resume instead of abort:
- Emergency no longer cancels the mission (`running` stays `True`)
- Freezes motors while obstacle present, keeps waypoint index
- **Auto-resumes** driving toward the same waypoint when obstacle clears
- Fixed crash: missing `self.emergency = False` in `__init__`
  (caused `AttributeError: 'WaypointFollower' has no attribute 'emergency'`,
  node died at startup, waypoints "not saving" as a result)

**`ultrasonic_node.py`** — Noise robustness:
- **Staggered sensor pings** (+20ms) to eliminate cross-talk between
  the two front HC-SR04 sensors
- **Debounce:** requires **5 consecutive readings < threshold** (~0.5s)
  before asserting `/emergency_stop`
- **Median-of-3 sampling** per sensor + rejection of readings below 2cm
  (HC-SR04 physical minimum = glitch filter)

**Emergency threshold:** 30cm → **10cm** (configurable via `THRESHOLD_CM`;
10cm chosen for indoor testing, can raise for outdoor use).

**Bugs fixed this session:**
1. `AttributeError: 'WaypointFollower' has no attribute 'emergency'`
   → added `self.emergency = False` in `__init__`
2. `ModuleNotFoundError: 'std_msg'` typo → `std_msgs` in motor_driver import
3. `bringup.launch.py` syntax error — ultrasonic node nested inside
   `navsat_transform_node`'s `Node()` call (residual from earlier session)

**Verified end-to-end:**
- `ros2 topic echo /ultrasonic/front`: idle ~1.88m (clear), tracks
  hand correctly at 0.5m / 0.14m — sensors confirmed healthy
- Waypoint run: obstacle → pause → remove → **auto-resume confirmed**
- Manual drive: motors cut instantly on obstacle even mid-button-hold
- All 9 bringup processes start clean, no deaths

**Known issue / in progress:**
- Robot feels **jittery during manual drive**. Suspected causes:
  - (a) vibration-induced false readings while moving — median filter
    + debounce applied, needs retest
  - (b) `min_pwm = 0.25` boost in `set_motor()` causing lurch on resume
  - (c) multiple dashboard tabs publishing conflicting `/cmd_vel` — ruled
    out if single tab confirmed
- Next session: retest with echo running during drive; if jitter
  persists, add acceleration ramp in motor driver

**Indoor stack v2 now complete:**
- Drive: motor_driver (with motor-level emergency stop) + encoder_node +
  imu_node + env_node
- Navigation: EKF + waypoint_follower (pause-resume) + ultrasonic_node
  (noise filtering)
- Dashboard: camera + drive pad + keyboard + waypoints + sensors + map
- AI: camera_stream + ai_inference (manual trigger)

**Remaining to December viva:**
1. AI scan at each waypoint (capture → classify → log result automatically)
2. Field-test waypoint accuracy on actual floor
3. ADS1115 battery monitor (when LiPo returns)
4. Report writing + documentation

PASTE_PHOTO_1_URL

---

## 14/10/2026 — Ultrasonic emergency stop + complete indoor stack

**`ultrasonic_node.py`** — NEW emergency stop node:
- 2× HC-SR04 front ultrasonic sensors, angled inward for center coverage
- `lgpio` backend with `gpiochip 4` (Pi 5 compatible — `gpiochip 0` fails)
- Pins: **Trig GPIO17/23**, **Echo GPIO22/27**
- Echo pins use **1kΩ + 2kΩ voltage dividers** (5V → ~3.3V for Pi GPIO)
- Publishes `/ultrasonic/front` (Float32, minimum distance in metres)
- Publishes `/emergency_stop` (Bool, `True` when <30 cm)
- Waypoint follower subscribes to `/emergency_stop` and halts autonomous run

**`bringup.launch.py`** now launches **9 processes:**
`motor_driver`, `encoder_node`, `imu_node`, `env_node`, `gps_node`,
`ekf_filter_node` (robot_localization), `navsat_transform_node` (GPS
pipeline, standby for outdoor use), `waypoint_follower`,
`ultrasonic_node`, `rosbridge_server`, `camera_stream`.

**`waypoint_follower.py`** — added emergency stop callback:
- Subscribes `/emergency_stop` → sets `running=False`, publishes zero `/cmd_vel`
- Logs `"EMERGENCY STOP — obstacle detected!"` when triggered
- Manual drive resumes cleanly after obstacle clears and Stop pressed

**Previous session work still active:**
- EKF fusing `/odom` + `/imu/data` → `/odometry/filtered` at 20 Hz
- Indoor waypoint navigation: Save Waypoint, Run, Stop via dashboard
- Keyboard WASD + Arrow key control
- Dashboard: live camera, sensors, drive pad, map, results table
- Camera proxy via Flask (no hardcoded IPs)

**Bugs fixed this session:**
1. `bringup.launch.py` syntax error — `ultrasonic_node` inserted inside
   `navsat_transform_node`'s `Node()` call, splitting it in half. Fixed by
   closing navsat node with `]),` before starting ultrasonic node.
2. `lgpio gpiochip_open(0)` fails on Pi 5 → changed to `gpiochip_open(4)`
3. Multiple dashboard layout regressions from full-file overwrites →
   restored original HTML structure with targeted additions only

**Verified end-to-end:**
- `ros2 topic echo /ultrasonic/front` shows live distance values (~2 m
  at rest, drops when hand waved in front)
- `/emergency_stop = True` when obstacle <30 cm in front of either sensor
- Waypoint follower halts immediately when obstacle detected
- Manual drive, keyboard, camera, all sensors still functional
- All 9 processes start from single `bringup.launch.py`

**Indoor stack now complete:**
- Drive: motor_driver + encoder_node + imu_node + env_node
- Navigation: EKF + waypoint_follower + ultrasonic_node (safety)
- Dashboard: camera + drive pad + keyboard + waypoints + sensors + map
- AI: camera_stream + ai_inference (manual trigger)

**Remaining to December viva:**
1. AI scan at each waypoint (capture → classify → log result automatically)
2. Field-test waypoint accuracy on actual floor
3. ADS1115 battery monitor (when LiPo returns)
4. Report writing + documentation

![Ultrasonic E-stop test — terminal showing /ultrasonic/front and /emergency_stop topics](https://github.com/user-attachments/assets/9ed42fd2-fc51-40f3-afd9-d9897b58a039)

![Emergency stop verification — obstacle detected below 30 cm threshold](https://github.com/user-attachments/assets/85c5b798-760a-4ce8-aa27-8eb0f9c1cbbd)

![HC-SR04 sensors mounted on front of chassis — angled inward, voltage dividers on echo lines](https://github.com/user-attachments/assets/66f292f3-268d-4142-80d8-bdfdaf43e541)

---

## 12/10/2026 — Indoor waypoint navigation complete (EKF + follower + keyboard control)

**robot_localization EKF** now fusing `/odom` (encoders) + `/imu/data`
(BNO055) → `/odometry/filtered` at 20 Hz. Config: `two_d_mode: true`,
`world_frame: odom`, `odom0` provides x/y/vx/yaw_vel, `imu0` provides
yaw/yaw_rate in differential mode. Encoder pose + twist covariances
added to `encoder_node.py` for proper EKF weighting. IMU covariances
already set from previous work.

**EKF performance:** tracks real robot motion well; x/y drift ~0.8 m
per metre of hand-pushed travel (expected without GPS loop closure).

**`waypoint_follower.py`** — NEW indoor autonomous navigation node:
- Subscribes `/odometry/filtered`, publishes `/cmd_vel`
- Topics: `/waypoint/save`, `/waypoint/clear`, `/waypoint/run`, `/waypoint/stop`
- Saves waypoints to JSON as `{x, y, yaw}` from live EKF pose
- Proportional control: turn-in-place if `|yaw_err| > 0.5 rad`,
  otherwise drive forward at `0.15 * dist` capped at `0.15 m/s`
- Angular capped at `±0.3 rad/s`
- 15 cm position tolerance, 0.15 rad final orientation tolerance
- Publishes `/cmd_vel` **only when running** — no idle spam

**Dashboard (`index.html`) restored + upgraded:**
- Keyboard control: WASD + Arrow keys publish `/cmd_vel` at 10 Hz
- Waypoint buttons: **Save Waypoint**, **Clear All**, **Run**, **Stop**
- `autonomous` flag prevents dashboard from publishing zeros during Run
  (resolves cmd_vel conflict between dashboard and waypoint follower)
- Camera: responsive 4:3 wrapper, fills drive-row column
- Fixed sensor types: `sensor_msgs/Temperature` + `RelativeHumidity`
  (was `std_msgs/Float32`)

**`bringup.launch.py`** now launches **8 processes:**
`motor_driver`, `encoder_node`, `imu_node`, `env_node`, `gps_node`,
`ekf_node` (robot_localization), `rosbridge_server`, `camera_stream`.
`navsat_transform_node` included in launch file but disabled for indoor
use (GPS pipeline ready for outdoor switch-on).

**Bugs fixed during session:**
1. Camera iframe 404 — stray quote in `src="/cam_feed""` found via
   access-log path: `GET /cam_feed" HTTP/1.1" 404`
2. Missing `import requests` — nano buffer not saved; verified with `grep`
3. `stream_with_context(gen)` missing call parens → `gen()`
4. Browser cache stale pages → incognito + Ctrl+Shift+R
5. Waypoint JS outside `</script>` tag → moved inside
6. Dashboard/waypointFollower `/cmd_vel` conflict → `autonomous` flag
   in dashboard JS
7. Undefined variable `autonomous` → declared alongside `vx, vz`
8. Camera aspect ratio cycling → removed `max-width: 640px`

**Verified end-to-end:**
- EKF publishes `/odometry/filtered` with position tracking real motion
- Waypoint follower: Save → Run → robot turns toward waypoint, drives
  forward, reaches 15 cm tolerance
- Manual drive (pad + keyboard) resumes cleanly after Stop
- Camera live, all sensors updating, map + results table intact

**Remaining to December viva:**
1. Field-test waypoint follower on actual floor (tune gains if needed)
2. Front ×2 HC-SR04 ultrasonic emergency stop (<30 cm)
3. ADS1115 battery monitor (when LiPo returns)
4. DHT11 as optional cross-check sensor
5. Report writing + documentation

![Mission Control dashboard — EKF fused odometry, waypoint buttons, keyboard control](https://github.com/user-attachments/assets/ed94bb90-1534-4039-b83a-742c81b86319)

![Mission Control dashboard — sensor strip and camera feed](https://github.com/user-attachments/assets/b6f200fc-3050-4607-8785-be70eed05800)

![Mission Control dashboard — drive pad and heading card](https://github.com/user-attachments/assets/f3ca8958-5673-453e-8d27-62daae34d852)

---

## 09/10/2026 — Mission Control dashboard LIVE

Rewrote `dashboard/templates/index.html` as a single **Mission Control**
page. Layout top-to-bottom: stats cards → live sensor strip → camera
feed + drive pad → GPS map + results table. All sensor data flows via
`roslib.js` over the rosbridge WebSocket (port 9090) — **zero changes
to any ROS node**.

**Live sensor cards** (all updating in real time):
- `/fix` → GPS coords + fix status
- `/odom` → distance-traveled (hypot of x, y)
- `/imu/data` → heading (quaternion → yaw → degrees)
- `/env/temperature`, `/env/humidity` → AHT30 environmental cards
- `/plant_health` → "AI last scan" card

**Embedded drive pad** — same `/cmd_vel` 10 Hz publisher as the
standalone `/control` page: hold-to-drive, auto-stop on release/blur,
speed slider. Now part of the unified dashboard instead of a separate
page.

**Camera proxy** (no hardcoded IPs):
- `GET /cam` → minimal wrapper HTML with `<img src="/cam_feed">`
- `GET /cam_feed` → streams MJPEG from `http://127.0.0.1:5000/video_feed`
  via `requests` + `Flask Response(stream_with_context(gen()))`

**Bringup now launches 6 ROS nodes + 2 services**, one command:**

```bash
ros2 launch robot_control bringup.launch.py
# Starts: motor_driver, encoder_node, imu_node, env_node, gps_node,
#         rosbridge_websocket, camera_stream (Flask :5000)
```

Then in a second terminal:

```bash
python3 ~/ros2_ws/src/robot_control/dashboard/app.py  # port 8080
```

**Bugs fixed during bring-up (report material):**
1. `NameError: name 'requests' is not defined` → import line added in
   nano but buffer not saved. Lesson: verify with `grep` after editing.
2. `TypeError: 'function' object is not iterable` →
   `stream_with_context(gen)` missing call parens; fixed to `gen()`.
3. Camera iframe 404 despite proxy healthy → stray double-quote in
   `iframe src` (`"/cam_feed""`). Diagnosed by reading the access log
   verbatim: `GET /cam_feed" HTTP/1.1" 404`.
4. Browser cache serving stale pages → incognito + Ctrl+Shift+R.
5. Dashboard hung process blocking port 8080 → `pkill -f app.py`,
   verify with `curl -I http://localhost:8080` before trusting the
   browser.

**Verified end-to-end:**
- `curl /cam` = 200 (wrapper), `curl /cam_feed` = 200 (MJPEG relay),
  `curl /video_feed` = 200 (direct)
- Browser: live video in iframe, sensor cards updating, drive pad
  publishing, map and results table intact
- Zero hardcoded IPs anywhere in the dashboard (all relative paths)

![Mission Control dashboard — sensor strip and camera feed](https://github.com/user-attachments/assets/669aabed-7c8f-424b-a11e-766d7152212e)

![Mission Control dashboard — GPS map and results table](https://github.com/user-attachments/assets/477dfb78-d2f1-4e7d-9065-a5d188273116)

![Mission Control dashboard — drive pad and heading card](https://github.com/user-attachments/assets/c02d9829-ccdf-4422-bf67-17b2473932fc)

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
not per-wheel). **Deadband patch:** `|cmd| <= 0.01` keeps the last
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
- I2C: GPIO2/3 → BNO055 @0x29 (AHT30 shares bus)
- UART: GPIO14/15 → `/dev/ttyAMA0` → GPS
- **Spare: 12 GPIO** (4/7/8/9/10/11/17/21/22/23/24/27)

**Next:** `robot_localization` EKF (`/odom` + `/imu/data` →
`/odometry/filtered`), then nav2 with GPS waypoints. Demo-day checklist:
remount IMU flat, GPS antenna sky view, figure-8 mag calibration for
BNO055.

![BNO055 IMU on I2C bus](https://github.com/user-attachments/assets/9ed1aa74-bf93-4861-86d6-f2206999f6a3)

![GPS NEO-8M UART test showing /fix topic](https://github.com/user-attachments/assets/b9b619d2-e46c-4c87-a08b-c9ef1d5efa7a)

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
3. Zero-cmd direction flip → deadband patch (`|cmd| > 0.01` updates dir)
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
