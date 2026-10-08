#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix, NavSatStatus
import serial

class GPSNode(Node):
    def __init__(self):
        super().__init__('gps_node')
        self.pub = self.create_publisher(NavSatFix, '/fix', 10)
        self.ser = serial.Serial('/dev/ttyAMA0', 9600, timeout=1)
        self.get_logger().info('GPS node started on /dev/ttyAMA0 @ 9600')

    def nmea_to_deg(self, coord, hemi):
        d = int(float(coord) // 100)
        m = float(coord) - d * 100
        deg = d + m / 60.0
        if hemi in ('S', 'W'):
            deg = -deg
        return deg

    def run(self):
        while rclpy.ok():
            try:
                line = self.ser.readline().decode('ascii', errors='replace').strip()
            except Exception:
                continue
            if not (line.startswith('$GNGGA') or line.startswith('$GPGGA')):
                continue
            parts = line.split(',')
            msg = NavSatFix()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = 'gps'
            fix_ok = (len(parts) > 9 and parts[6] not in ('0', '')
                      and parts[2] and parts[4])
            if fix_ok:
                msg.status.status = NavSatStatus.STATUS_FIX
                msg.latitude = self.nmea_to_deg(parts[2], parts[3])
                msg.longitude = self.nmea_to_deg(parts[4], parts[5])
                msg.altitude = float(parts[9]) if parts[9] else 0.0
                self.get_logger().info(
                    f'GPS FIX: {msg.latitude:.6f}, {msg.longitude:.6f}')
            else:
                msg.status.status = NavSatStatus.STATUS_NO_FIX
                msg.latitude = 0.0
                msg.longitude = 0.0
                msg.altitude = 0.0
            msg.position_covariance_type = NavSatFix.COVARIANCE_TYPE_UNKNOWN
            self.pub.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = GPSNode()
    try:
        node.run()
    except KeyboardInterrupt:
        pass
    finally:
        node.ser.close()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
