#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from gpiozero import PWMOutputDevice, DigitalOutputDevice

class MotorDriver(Node):
    def __init__(self):
        super().__init__('motor_driver')
        
        self.max_speed = 0.8
        self.wheel_separation = 0.18
        
        self.left_pwm = PWMOutputDevice(12)
        self.left_in1 = DigitalOutputDevice(16)
        self.left_in2 = DigitalOutputDevice(20)
        
        self.right_pwm = PWMOutputDevice(18)
        self.right_in1 = DigitalOutputDevice(25)
        self.right_in2 = DigitalOutputDevice(26)
        
        self.subscription = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_vel_callback,
            10
        )
        
        self.timer = self.create_timer(1.0, self.watchdog_callback)
        self.last_cmd_time = self.get_clock().now()
        
        self.get_logger().info('Motor driver ready. MAX SPEED: {:.0f}%'.format(self.max_speed * 100))

    def cmd_vel_callback(self, msg):
        self.last_cmd_time = self.get_clock().now()
        
        linear = msg.linear.x
        angular = msg.angular.z
        
        left_speed = linear - (angular * self.wheel_separation / 2.0)
        right_speed = linear + (angular * self.wheel_separation / 2.0)
        
        left_speed = max(-self.max_speed, min(self.max_speed, left_speed))
        right_speed = max(-self.max_speed, min(self.max_speed, right_speed))
        
        self.set_motor(self.left_pwm, self.left_in1, self.left_in2, left_speed)
        self.set_motor(self.right_pwm, self.right_in1, self.right_in2, right_speed)

    def set_motor(self, pwm, in1, in2, speed):
        min_pwm = 0.25
        
        if abs(speed) > 0 and abs(speed) < min_pwm:
            speed = min_pwm if speed > 0 else -min_pwm
        
        if speed > 0:
            in1.on()
            in2.off()
            pwm.value = abs(speed)
        elif speed < 0:
            in1.off()
            in2.on()
            pwm.value = abs(speed)
        else:
            in1.off()
            in2.off()
            pwm.value = 0.0

    def watchdog_callback(self):
        now = self.get_clock().now()
        elapsed = (now - self.last_cmd_time).nanoseconds / 1e9
        if elapsed > 1.0:
            self.set_motor(self.left_pwm, self.left_in1, self.left_in2, 0.0)
            self.set_motor(self.right_pwm, self.right_in1, self.right_in2, 0.0)
            self.get_logger().warn('Watchdog: motors stopped')

    def destroy_node(self):
        self.set_motor(self.left_pwm, self.left_in1, self.left_in2, 0.0)
        self.set_motor(self.right_pwm, self.right_in1, self.right_in2, 0.0)
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = MotorDriver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
