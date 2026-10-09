from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import ExecuteProcess

def generate_launch_description():
    return LaunchDescription([
        Node(package='robot_control', executable='motor_driver',
             name='motor_driver', output='screen'),
        Node(package='robot_control', executable='encoder_node',
             name='encoder_node', output='screen'),
        Node(package='robot_control', executable='imu_node',
             name='imu_node', output='screen'),
        Node(package='robot_control', executable='env_node',
             name='env_node', output='screen'),
        Node(package='robot_control', executable='gps_node',
             name='gps_node', output='screen'),
        ExecuteProcess(cmd=['ros2', 'launch', 'rosbridge_server',
                            'rosbridge_websocket_launch.xml'],
                       output='screen'),
        ExecuteProcess(cmd=['python3',
                            '/home/yvette_pi/ros2_ws/src/robot_control/robot_control/camera_stream.py'],
                       output='screen'),
    ])
