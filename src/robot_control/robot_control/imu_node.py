#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from smbus2 import SMBus
import math
import time

class ImuNode(Node):
    def __init__(self):
        super().__init__('imu_node')
        self.bus = SMBus(1)
        self.addr = 0x29   # BNO055 (address pin high)

        # Config mode -> set units -> NDOF fusion mode
        self.bus.write_byte_data(self.addr, 0x3D, 0x00)  # CONFIG_MODE
        time.sleep(0.02)
        self.bus.write_byte_data(self.addr, 0x3E, 0x00)  # normal power
        self.bus.write_byte_data(self.addr, 0x3B, 0x00)  # m/s^2, dps, degrees
        self.bus.write_byte_data(self.addr, 0x3D, 0x0C)  # NDOF (full fusion)
        time.sleep(1.0)

        self.pub = self.create_publisher(Imu, '/imu/data', 10)
        self.create_timer(0.05, self.update)  # 20 Hz

        cal = self.bus.read_byte_data(self.addr, 0x35)  # CALIB_STAT
        self.get_logger().info(
            f'BNO055 @0x29 started, calib status 0x{cal:02x} '
            f'(0xff = fully calibrated, self-calibrates over time)')

    def rd16(self, reg):
        b = self.bus.read_i2c_block_data(self.addr, reg, 2)
        v = (b[1] << 8) | b[0]
        return v - 65536 if v >= 32768 else v

    def update(self):
        imu = Imu()
        imu.header.stamp = self.get_clock().now().to_msg()
        imu.header.frame_id = 'imu_link'

        # Fused quaternion (w,x,y,z), scale 1/16384
        imu.orientation.w = self.rd16(0x20) / 16384.0
        imu.orientation.x = self.rd16(0x22) / 16384.0
        imu.orientation.y = self.rd16(0x24) / 16384.0
        imu.orientation.z = self.rd16(0x26) / 16384.0
        for i in (0, 4, 8):
            imu.orientation_covariance[i] = 0.01

        # Gyro (dps -> rad/s), scale 1/16
        imu.angular_velocity.x = self.rd16(0x14) / 16.0 * math.pi / 180.0
        imu.angular_velocity.y = self.rd16(0x16) / 16.0 * math.pi / 180.0
        imu.angular_velocity.z = self.rd16(0x18) / 16.0 * math.pi / 180.0
        for i in (0, 4, 8):
            imu.angular_velocity_covariance[i] = 0.02

        # Accelerometer (m/s^2), scale 1/100
        imu.linear_acceleration.x = self.rd16(0x08) / 100.0
        imu.linear_acceleration.y = self.rd16(0x0A) / 100.0
        imu.linear_acceleration.z = self.rd16(0x0C) / 100.0
        for i in (0, 4, 8):
            imu.linear_acceleration_covariance[i] = 0.5

        self.pub.publish(imu)

def main(args=None):
    rclpy.init(args=args)
    node = ImuNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
