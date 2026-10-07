#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32MultiArray
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped, Twist
from gpiozero import DigitalInputDevice
import math
import tf2_ros

class EncoderNode(Node):
    def __init__(self):
        super().__init__('encoder_node')

        # === CALIBRATION ===
        self.ticks_per_meter = 90.0   # 64 ticks/rev, corrected by floor test
        self.wheel_separation = 0.18  # same as motor_driver

        # Direction per side comes from /cmd_vel (count-only encoders
        # cannot sense direction themselves)
        self.dir_left = 1
        self.dir_right = 1
        self.create_subscription(Twist, '/cmd_vel', self.
cmd_callback, 10)

        self.pins = {'FL': 5, 'RL': 6, 'FR': 13, 'RR': 19}
        self.counts = {k: 0 for k in self.pins}
        self.encoders = {}
        for name, pin in self.pins.items():
            e = DigitalInputDevice(pin, pull_up=True)
            e.when_activated = self.make_tick(name)
            self.encoders[name] = e

        # Odometry state
        self.x = 0.0; self.y = 0.0; self.th = 0.0
        self.last_left = 0.0; self.last_right = 0.0
        self.last_time = self.get_clock().now()

        self.tick_pub = self.create_publisher(Int32MultiArray, '/wheel_ticks', 10)
        self.odom_pub = self.create_publisher(Odometry, '/odom', 10)
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)
        self.create_timer(0.1, self.update)  # 10 Hz

        self.get_logger().info('Encoder node started: FL=5 RL=6 FR=13 RR=19')

    def cmd_callback(self, msg):
        # Same mixing as motor_driver: which way is each side commanded?
        x, z = msg.linear.x, msg.angular.z
        sep = self.wheel_separation
        l = x - z * sep / 2.0
        r = x + z * sep / 2.0
        # Deadband: keep last direction while stopped/coasting —
        # a zero command must NOT flip the sign
        if l > 0.01:
            self.dir_left = 1
        elif l < -0.01:
            self.dir_left = -1
        if r > 0.01:
            self.dir_right = 1
        elif r < -0.01:
            self.dir_right = -1
    def make_tick(self, name):
        def tick():
            if name in ('FL', 'RL'):
                self.counts[name] += self.dir_left
            else:
                self.counts[name] += self.dir_right
        return tick

    def update(self):
        left = (self.counts['FL'] + self.counts['RL']) / 2.0
        right = (self.counts['FR'] + self.counts['RR']) / 2.0

        msg = Int32MultiArray()
        msg.data = [self.counts['FL'], self.counts['RL'],
                    self.counts['FR'], self.counts['RR']]
        self.tick_pub.publish(msg)

        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds / 1e9
        if dt <= 0:
            return
        d_left = (left - self.last_left) / self.ticks_per_meter
        d_right = (right - self.last_right) / self.ticks_per_meter
        self.last_left, self.last_right, self.last_time = left, right, now

        dist = (d_left + d_right) / 2.0
        dth = (d_right - d_left) / self.wheel_separation
        self.th += dth
        self.x += dist * math.cos(self.th)
        self.y += dist * math.sin(self.th)

        odom = Odometry()
        odom.header.stamp = now.to_msg()
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_link'
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        qz = math.sin(self.th / 2.0); qw = math.cos(self.th / 2.0)
        odom.pose.pose.orientation.z = qz
        odom.pose.pose.orientation.w = qw
        odom.twist.twist.linear.x = dist / dt
        odom.twist.twist.angular.z = dth / dt
        self.odom_pub.publish(odom)

        t = TransformStamped()
        t.header.stamp = now.to_msg()
        t.header.frame_id = 'odom'
        t.child_frame_id = 'base_link'
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.rotation.z = qz
        t.transform.rotation.w = qw
        self.tf_broadcaster.sendTransform(t)

def main(args=None):
    rclpy.init(args=args)
    node = EncoderNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
