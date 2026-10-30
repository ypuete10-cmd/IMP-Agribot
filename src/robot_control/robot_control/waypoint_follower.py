#!/usr/bin/env python3
"""
Waypoint follower — indoor odometry-based navigation.
Subscribes to /odometry/filtered, publishes /cmd_vel to reach saved waypoints.
Triggers AI scan at each waypoint via /waypoint/reached topic.
"""
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
from std_msgs.msg import Empty, Bool, Float32MultiArray
import math, json, os

WP_FILE = os.path.expanduser('~/ros2_ws/src/robot_control/dashboard/data/waypoints.json')


def yaw_from_quaternion(q):
    siny = 2.0 * (q.w * q.z + q.x * q.y)
    cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny, cosy)


class WaypointFollower(Node):
    def __init__(self):
        super().__init__('waypoint_follower')
        self.sub = self.create_subscription(Odometry, '/odometry/filtered', self.odom_cb, 10)
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.create_subscription(Empty, '/waypoint/save', self.save_cb, 10)
        self.create_subscription(Empty, '/waypoint/clear', self.clear_cb, 10)
        self.create_subscription(Bool, '/waypoint/run', self.run_cb, 10)
        self.create_subscription(Bool, '/waypoint/stop', self.stop_cb, 10)
        self.create_subscription(Bool, '/emergency_stop', self.emergency_cb, 10)
        self.reached_pub = self.create_publisher(Float32MultiArray, '/waypoint/reached', 10)
        self.create_subscription(Empty, '/waypoint/scan_done', self.scan_done_cb, 10)

        self.timer = self.create_timer(0.1, self.loop)  # 10 Hz
        self.x = self.y = self.yaw = 0.0
        self.waypoints = self.load()
        self.running = False
        self.emergency = False
        self.scanning = False
        self.current_idx = 0
        self.near_count = 0

        self.get_logger().info('Waypoint follower ready. %d waypoints loaded.' % len(self.waypoints))

    def load(self):
        if not os.path.exists(WP_FILE):
            return []
        with open(WP_FILE) as f:
            return json.load(f)

    def save(self):
        os.makedirs(os.path.dirname(WP_FILE), exist_ok=True)
        with open(WP_FILE, 'w') as f:
            json.dump(self.waypoints, f, indent=2)

    def odom_cb(self, msg):
        self.x = msg.pose.pose.position.x
        self.y = msg.pose.pose.position.y
        self.yaw = yaw_from_quaternion(msg.pose.pose.orientation)

    def save_cb(self, _):
        wp = {'x': self.x, 'y': self.y, 'yaw': self.yaw}
        self.waypoints.append(wp)
        self.save()
        self.get_logger().info('Saved waypoint %d: x=%.3f y=%.3f yaw=%.2f' %
                                (len(self.waypoints), wp['x'], wp['y'], wp['yaw']))

    def clear_cb(self, _):
        self.waypoints = []
        self.save()
        self.get_logger().info('Waypoints cleared')

    def run_cb(self, msg):
        if msg.data and self.waypoints:
            self.running = True
            self.current_idx = 0
            self.near_count = 0
            self.get_logger().info('Autonomous run started: %d waypoints' % len(self.waypoints))
        else:
            self.running = False
            self.cmd_pub.publish(Twist())

    def stop_cb(self, _):
        self.running = False
        self.cmd_pub.publish(Twist())
        self.get_logger().info('Stopped')

    def loop(self):
        if self.emergency or self.scanning:
            self.cmd_pub.publish(Twist())
            return
        if not self.running or not self.waypoints:
            return

        wp = self.waypoints[self.current_idx]
        dx = wp['x'] - self.x
        dy = wp['y'] - self.y
        dist = math.hypot(dx, dy)
        target_yaw = math.atan2(dy, dx)
        yaw_err = target_yaw - self.yaw
        while yaw_err > math.pi: yaw_err -= 2 * math.pi
        while yaw_err < -math.pi: yaw_err += 2 * math.pi

        cmd = Twist()
        self.get_logger().info('WP %d/%d: pos=(%.2f,%.2f) yaw=%.2f | dist=%.2f yaw_err=%.2f' % (
            self.current_idx, len(self.waypoints), self.x, self.y, self.yaw, dist, yaw_err))

        if dist > 0.15:  # 15 cm tolerance
            if abs(yaw_err) > 0.8:
                cmd.angular.z = max(-0.4, min(0.4, 0.8 * yaw_err))
                cmd.linear.x = 0.0
            else:
                cmd.linear.x = max(0.0, min(0.3, 0.5 * dist))
                cmd.angular.z = max(-0.3, min(0.3, 0.5 * yaw_err))
        else:
            # Arrived at waypoint - trigger AI scan for EVERY waypoint (including last)
            self.near_count = 0
            self.current_idx += 1
            msg = Float32MultiArray()
            msg.data = [float(self.current_idx), float(self.x), float(self.y)]
            self.reached_pub.publish(msg)
            self.scanning = True
            self.get_logger().info('Reached waypoint %d/%d — scanning' %
                                    (self.current_idx, len(self.waypoints)))

        self.get_logger().info('CMD: lin=%.3f ang=%.3f' % (cmd.linear.x, cmd.angular.z))
        self.cmd_pub.publish(cmd)

    def scan_done_cb(self, _):
        self.scanning = False
        if self.current_idx >= len(self.waypoints):
            self.running = False
            self.get_logger().info('All waypoints reached!')
        else:
            self.get_logger().info('Scan done — resuming to waypoint %d/%d' %
                                    (self.current_idx + 1, len(self.waypoints)))

    def emergency_cb(self, msg):
        if msg.data and not self.emergency:
            self.get_logger().error('EMERGENCY STOP — pausing, will resume when clear')
        self.emergency = msg.data


def main(args=None):
    rclpy.init(args=args)
    node = WaypointFollower()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
