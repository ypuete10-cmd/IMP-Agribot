#!/usr/bin/env python3
"""
Front ultrasonic sensors — emergency stop.
2× HC-SR04 angled inward for center coverage.
Publishes: /ultrasonic/front (min distance in meters)
           /emergency_stop (Bool, True if <30cm)
"""
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Float32
import lgpio
import time

TRIG_PINS = [17, 23]   # front-left, front-right
ECHO_PINS = [22, 27]
THRESHOLD_CM = 10.0
SPEED_SOUND = 343.0


class UltrasonicNode(Node):
    def __init__(self):
        super().__init__('ultrasonic_node')
        self.stop_pub = self.create_publisher(Bool, '/emergency_stop', 10)
        self.dist_pub = self.create_publisher(Float32, '/ultrasonic/front', 10)
        self.timer = self.create_timer(0.1, self.loop)
        self.close_count = 0

        self.chip = lgpio.gpiochip_open(4)
        for t in TRIG_PINS:
            lgpio.gpio_claim_output(self.chip, t)
            lgpio.gpio_write(self.chip, t, 0)
        for e in ECHO_PINS:
            lgpio.gpio_claim_input(self.chip, e)

        self.get_logger().info('Ultrasonic ready. Pins: trig=%s echo=%s' % (TRIG_PINS, ECHO_PINS))

    def measure(self, trig, echo):
        lgpio.gpio_write(self.chip, trig, 1)
        time.sleep(0.00001)
        lgpio.gpio_write(self.chip, trig, 0)

        start = time.time()
        timeout = start + 0.04
        while lgpio.gpio_read(self.chip, echo) == 0:
            start = time.time()
            if start > timeout:
                return float('inf')

        end = time.time()
        timeout = end + 0.04
        while lgpio.gpio_read(self.chip, echo) == 1:
            end = time.time()
            if end > timeout:
                return float('inf')

        return (end - start) * SPEED_SOUND / 2.0

    def loop(self):
        min_dist = float('inf')
        for t, e in zip(TRIG_PINS, ECHO_PINS):
            samples = sorted(self.measure(t, e) for _ in range(3))  # median of 3
            d = samples[1]
            if d < 0.02:   # below sensor minimum = glitch, ignore
                continue
            if d < min_dist:
                min_dist = d
            time.sleep(0.02)

        dmsg = Float32()
        dmsg.data = min_dist
        self.dist_pub.publish(dmsg)

        if min_dist < (THRESHOLD_CM / 100.0):
            self.close_count += 1
        else:
            self.close_count = 0

        stop = Bool()
        stop.data = self.close_count >= 5  # 3 consecutive readings (~0.3s)
        self.stop_pub.publish(stop)

        if stop.data:
            self.get_logger().warning('OBSTACLE: %.1f cm — STOP' % (min_dist * 100))


def main(args=None):
    rclpy.init(args=args)
    node = UltrasonicNode()
    try:
        rclpy.spin(node)
    finally:
        lgpio.gpiochip_close(node.chip)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
