#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import cv2
import numpy as np
import json

try:
    import ai_edge_litert.interpreter as tflite
except ImportError:
    import tflite_runtime.interpreter as tflite


class AiInference(Node):
    def __init__(self):
        super().__init__('ai_inference')

        # Parameters
        self.declare_parameter('model_path', '/home/yvette_pi/plant_health.tflite')
        self.declare_parameter('class_names_path', '/home/yvette_pi/class_names.json')
        self.declare_parameter('camera_index', 0)
        self.declare_parameter('interval_sec', 2.0)  # classify every 2s

        model_path = self.get_parameter('model_path').value
        classes_path = self.get_parameter('class_names_path').value
        cam_idx = self.get_parameter('camera_index').value
        interval = self.get_parameter('interval_sec').value

        # Load model
        self.interp = tflite.Interpreter(model_path=model_path, num_threads=4)
        self.interp.allocate_tensors()
        self.inp = self.interp.get_input_details()[0]
        self.out = self.interp.get_output_details()[0]
        with open(classes_path) as f:
            self.class_names = json.load(f)

        # Camera
        self.cap = cv2.VideoCapture(cam_idx)
        # Warm up camera
        for _ in range(5):
            self.cap.read()

        self.publisher = self.create_publisher(String, '/plant_health', 10)
        self.timer = self.create_timer(interval, self.classify)
        self.get_logger().info(
            f'AI inference running | model: {model_path} | {len(self.class_names)} classes')

    def classify(self):
        ret, frame = self.cap.read()
        if not ret or frame is None:
            self.get_logger().warn('Frame capture failed, skipping')
            return

        img = cv2.resize(frame, (224, 224))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = np.expand_dims(img.astype(np.float32), 0)

        self.interp.set_tensor(self.inp['index'], img)
        self.interp.invoke()
        pred = self.interp.get_tensor(self.out['index'])[0]

        top = int(np.argmax(pred))
        confidence = float(pred[top])
        if confidence < 0.60:
            result = {'class': 'unknown_no_plant', 'confidence': round(confidence, 3)}
        else:
            result = {'class': self.class_names[top], 'confidence': round(confidence, 3)}
        msg = String()
        msg.data = json.dumps(result)
        self.publisher.publish(msg)
        self.get_logger().info(f"{result['class']} ({result['confidence']*100:.1f}%)")

    def destroy_node(self):
        self.cap.release()
        super().destroy_node()


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
