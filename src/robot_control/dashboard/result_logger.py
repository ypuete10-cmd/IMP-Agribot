#!/usr/bin/env python3
"""
Result logger node — appends plant classification results to the
dashboard data file (data/results.json).

SCAFFOLD MODE: simulates one waypoint scan every 10 s.

LATER — replace simulate_scan() with real subscriptions:
  GPS      : sensor_msgs/NavSatFix on /fix        -> lat, lon
  Classifier: your AI node's result topic          -> classification, confidence
  Camera   : capture service                      -> image filename
"""
import json, os, random
from datetime import datetime
import rclpy
from rclpy.node import Node

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, 'data', 'results.json')

class ResultLogger(Node):
    def __init__(self):
        super().__init__('result_logger')
        self.declare_parameter('simulate', True)
        self.simulate = self.get_parameter('simulate').get_parameter_value().bool_value
        self.wp = 0
        if self.simulate:
            self.timer = self.create_timer(10.0, self.simulate_scan)
            self.get_logger().info('Result logger in SIMULATE mode (1 scan / 10s)')

    def simulate_scan(self):
        """DELETE THIS when real sensors are wired — replace with subscriptions."""
        self.wp += 1
        result = {
            'waypoint': f'WP-{self.wp:02d}',
            'lat': 1.35042 + random.uniform(-0.0004, 0.0004),
            'lon': 103.68241 + random.uniform(-0.0004, 0.0004),
            'classification': random.choices(['healthy', 'early_blight'],
                                             weights=[7, 3])[0],
            'confidence': round(random.uniform(0.75, 0.98), 2),
            'timestamp': datetime.now().isoformat(timespec='seconds'),
        }
        self.log_result(result)
        self.get_logger().info(
            f"Logged {result['waypoint']}: {result['classification']} "
            f"({result['confidence']:.2f})")

    def log_result(self, result):
        with open(DATA) as f:
            data = json.load(f)
        result['id'] = max((x['id'] for x in data['results']), default=0) + 1
        data['results'].append(result)
        data['updated'] = datetime.now().isoformat(timespec='seconds')
        tmp = DATA + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, DATA)

def main(args=None):
    rclpy.init(args=args)
    node = ResultLogger()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
