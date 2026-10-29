#!/usr/bin/env python3
"""
AI inference — event-driven scanning at waypoints.

Subscribes /waypoint/reached (Float32MultiArray [index, x, y]):
  1. Grabs latest camera frame (/tmp/latest_frame.jpg, written by camera_stream)
  2. Classifies with TFLite model
  3. Appends result to dashboard/data/results.json
  4. Publishes /plant_health (String, JSON)
  5. Publishes /waypoint/scan_done (Empty) -> follower resumes

Frame source is a shared JPEG file so this node never touches
the camera hardware (camera_stream owns it).
"""
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Empty, Float32MultiArray
import cv2
import numpy as np
import json
import os
from datetime import datetime

try:
    import ai_edge_litert.interpreter as tflite
except ImportError:
    import tflite_runtime.interpreter as tflite

RESULTS_PATH = os.path.expanduser(
    '~/ros2_ws/src/robot_control/dashboard/data/results.json')
FRAME_PATH = '/tmp/latest_frame.jpg'
CONF_THRESHOLD = 0.60


class AiInference(Node):
    def __init__(self):
        super().__init__('ai_inference')

        self.declare_parameter('model_path', '/home/yvette_pi/plant_health.tflite')
        self.declare_parameter('class_names_path', '/home/yvette_pi/class_names.json')

        model_path = self.get_parameter('model_path').value
        classes_path = self.get_parameter('class_names_path').value

        self.interp = tflite.Interpreter(model_path=model_path, num_threads=4)
        self.interp.allocate_tensors()
        self.inp = self.interp.get_input_details()[0]
        self.out = self.interp.get_output_details()[0]
        with open(classes_path) as f:
            self.class_names = json.load(f)

        self.busy = False
        self.health_pub = self.create_publisher(String, '/plant_health', 10)
        self.done_pub = self.create_publisher(Empty, '/waypoint/scan_done', 10)
        self.create_subscription(Float32MultiArray, '/waypoint/reached',
                                 self.reached_cb, 10)
        self.get_logger().info(
            f'AI inference ready | {len(self.class_names)} classes | '
            'waiting for /waypoint/reached triggers')

    def reached_cb(self, msg):
        if self.busy:
            return
        self.busy = True
        idx = int(msg.data[0])
        x = float(msg.data[1])
        y = float(msg.data[2])
        try:
            result = self.classify()
            self.log_result(idx, x, y, result)
            s = String()
            s.data = json.dumps(result)
            self.health_pub.publish(s)
            self.get_logger().info(
                f"WP-{idx:02d}: {result['class']} "
                f"({result['confidence']*100:.1f}%)")
        except Exception as e:
            self.get_logger().error(f'Scan failed: {e}')
        self.done_pub.publish(Empty())
        self.busy = False

    def classify(self):
        frame = cv2.imread(FRAME_PATH)
        if frame is None:
            raise RuntimeError(f'No frame at {FRAME_PATH} '
                               '(is camera_stream running?)')
        img = cv2.resize(frame, (224, 224))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = np.expand_dims(img.astype(np.float32), 0)
        self.interp.set_tensor(self.inp['index'], img)
        self.interp.invoke()
        pred = self.interp.get_tensor(self.out['index'])[0]
        top = int(np.argmax(pred))
        conf = float(pred[top])
        if conf < CONF_THRESHOLD:
            return {'class': 'unknown_no_plant', 'confidence': round(conf, 3)}
        return {'class': self.class_names[top], 'confidence': round(conf, 3)}

    def log_result(self, idx, x, y, result):
        try:
            with open(RESULTS_PATH) as f:
                data = json.load(f)
        except Exception:
            data = {'mission_id': 'INDOOR-RUN', 'updated': '', 'results': []}
        data['results'].append({
            'id': len(data['results']) + 1,
            'waypoint': f'WP-{idx:02d}',
            'timestamp': datetime.now().isoformat(timespec='seconds'),
            'lat': 0.0,
            'lon': 0.0,
            'x': round(x, 3),
            'y': round(y, 3),
            'classification': result['class'],
            'confidence': result['confidence'],
        })
        data['updated'] = datetime.now().isoformat(timespec='seconds')
        tmp = RESULTS_PATH + '.tmp'          # atomic write: Flask never
        with open(tmp, 'w') as f:            # reads a half-written file
            json.dump(data, f, indent=2)
        os.replace(tmp, RESULTS_PATH)


def main(args=None):
    rclpy.init(args=args)
    node = AiInference()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
