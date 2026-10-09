#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Temperature, RelativeHumidity
from smbus2 import SMBus, i2c_msg
import time

AHT20_ADDR = 0x38

class EnvNode(Node):
    def __init__(self):
        super().__init__('env_node')
        self.bus = SMBus(1)
        time.sleep(0.05)  # AHT20 power-on settle

        # Initialize (calibration enable)
        self.bus.write_i2c_block_data(AHT20_ADDR, 0xBE, [0x08, 0x00])
        time.sleep(0.05)

        self.temp_pub = self.create_publisher(Temperature, '/env/temperature', 10)
        self.hum_pub = self.create_publisher(RelativeHumidity, '/env/humidity', 10)
        self.create_timer(2.0, self.update)  # 2 Hz is plenty for air

        self.get_logger().info('env_node started (AHT20 @ 0x38: temp + humidity)')

    def update(self):
        try:
            # Trigger measurement
            self.bus.write_i2c_block_data(AHT20_ADDR, 0xAC, [0x33, 0x00])
            time.sleep(0.1)
            m = i2c_msg.read(AHT20_ADDR, 7)   # AHT30 frame = 7 bytes
            self.bus.i2c_rdwr(m)
            d = list(m)
            if d[0] & 0x80:                    # busy flag
                return
            hum_raw = (d[1] << 12) | (d[2] << 4) | (d[3] >> 4)
            tmp_raw = ((d[3] & 0x0F) << 16) | (d[4] << 8) | d[5]
            humidity = hum_raw / 1048576.0 * 100.0
            celsius = tmp_raw / 1048576.0 * 200.0 - 50.0

            t = Temperature()
            t.header.stamp = self.get_clock().now().to_msg()
            t.temperature = celsius
            self.temp_pub.publish(t)

            h = RelativeHumidity()
            h.header.stamp = t.header.stamp
            h.relative_humidity = humidity / 100.0
            self.hum_pub.publish(h)
        except Exception as e:
            self.get_logger().warn(f'AHT20 read failed: {e}')

def main(args=None):
    rclpy.init(args=args)
    node = EnvNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
