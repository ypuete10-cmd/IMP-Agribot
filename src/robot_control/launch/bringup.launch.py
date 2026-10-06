from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import ExecuteProcess

def generate_launch_description():
    return LaunchDescription([
        # Motor driver
        Node(
            package='robot_control',
            executable='motor_driver',
            name='motor_driver',
            output='screen',
        ),

        # rosbridge (for the web dashboard)
        ExecuteProcess(
            cmd=['ros2', 'launch', 'rosbridge_server',
                 'rosbridge_websocket_launch.xml'],
            output='screen',
        ),

        # Flask camera stream + dashboard
        ExecuteProcess(
            cmd=['python3',
                 '/home/yvette_pi/ros2_ws/src/robot_control/robot_control/camera_stream.py'],
            output='screen',
        ),

        # Future nodes get added here:
        # Node(package='robot_control', executable='gps_node', ...),
        # Node(package='robot_control', executable='ai_inference', ...),
    ])
