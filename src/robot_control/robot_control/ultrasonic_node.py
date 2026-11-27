#!/usr/bin/env python
"""
Front ultrasonic sensors — emergency stop.
2x HC-SR04 angled inward for center coverage.
Publishes: /ultrasonic/front (min distance in meters)
           /emergency_stop (Bool, True if <30cm)

v2: callback kept well under the timer period so ROS never
    queues callbacks (previously the callback overran its
    0.1 s timer -> node never idled -> ~80% CPU and stale
    emergency_stop publications). Echo timeout reduced to
    0.02 s (3.4 m range, beyond indoor need); median-of-3
    is now rolling across the last 3 loops instead of 3
    blocking samples inside one loop.
"""
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Float32
import lgpio
import time
from collections import deque

TRIG_PINS = [17, 23]   # front-left, front-right
ECHO_PINS = [22, 27]
THRESHOLD_CM = 30.0
SPEED_SOUND = 343.0
ECHO_TIMEOUT = 0.02    # 0.02 s ~= 3.4 m max range (indoor: plenty)


class UltrasonicNode(Node):
    def __init__(self):
        super().__init__('ultrasonic_node')
        self.stop_pub = self.create_publisher(Bool, '/emergency_stop', 10)
        self.dist_pub = self.create_publisher(Float32, '/ultrasonic/front', 10)
        self.timer = self.create_timer(0.1, self.loop)
        self.close_count = 0
        self.open_count = 0
        self.last_stop = False
        # rolling median window per sensor (3 most recent loop readings)
        self.hist = [deque(maxlen=3), deque(maxlen=3)]

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
        timeout = start + ECHO_TIMEOUT
        while lgpio.gpio_read(self.chip, echo) == 0:
            start = time.time()
            if start > timeout:
                return float('inf')

        end = time.time()
        timeout = end + ECHO_TIMEOUT
        while lgpio.gpio_read(self.chip, echo) == 1:
            end = time.time()
            if end > timeout:
                return float('inf')

        dist_m = (end - start) * SPEED_SOUND / 2.0
        if dist_m > 3.0:      # beyond sane indoor range = artifact
            return float('inf')
        return dist_m

    def loop(self):
        min_dist = float('inf')
        for i, (t, e) in enumerate(zip(TRIG_PINS, ECHO_PINS)):
            d = self.measure(t, e)
            self.hist[i].append(d)
            samples = sorted(self.hist[i])
            d = samples[len(samples) // 2]      # median of last <=3 readings

            if d < 0.02:
                d = 0.01
            if d < min_dist:
                min_dist = d

        dmsg = Float32()
        dmsg.data = min_dist
        self.dist_pub.publish(dmsg)

        if min_dist < (THRESHOLD_CM / 100.0):
            self.close_count += 1
            self.open_count = 0
        else:
            self.open_count += 1
            self.close_count = 0

        if self.close_count >= 3:
            self.last_stop = True
        elif self.open_count >= 10:
            self.last_stop = False

        stop = Bool()
        stop.data = self.last_stop
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
