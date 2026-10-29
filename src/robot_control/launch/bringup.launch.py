#!/usr/bin/env python3
"""
Agribot bringup — launches all robot nodes.
10 processes: motor, encoder, imu, env, gps, waypoint_follower,
ekf, navsat_transform, ultrasonic, ai_inference
plus rosbridge (WebSocket) and camera_stream (Flask MJPEG).
"""
import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import ExecuteProcess

EKF_PARAMS = os.path.expanduser('~/ros2_ws/src/robot_control/config/ekf.yaml')


def generate_launch_description():
    return LaunchDescription([
        # --- Hardware interface ---
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

        # --- Navigation ---
        Node(package='robot_control', executable='waypoint_follower',
             name='waypoint_follower', output='screen'),
        Node(package='robot_localization', executable='ekf_node',
             name='ekf_filter_node', output='screen',
             parameters=[EKF_PARAMS]),
        Node(package='robot_localization', executable='navsat_transform_node',
             name='navsat_transform_node', output='screen',
             parameters=[{
                 'frequency': 10.0,
                 'delay': 3.0,
                 'magnetic_declination_radians': 0.0,
                 'yaw_offset': 0.0,
                 'zero_altitude': True,
                 'broadcast_utm_transform': False,
                 'publish_filtered_gps': True,
                 'use_odometry_yaw': True,
                 'wait_for_datum': False,
             }],
             remappings=[
                 ('/imu/data', '/imu/data'),
                 ('/gps/fix', '/fix'),
                 ('/odometry/filtered', '/odometry/filtered'),
             ]),

        # --- Safety ---
        Node(package='robot_control', executable='ultrasonic_node',
             name='ultrasonic_node', output='screen'),

        # --- AI ---
        Node(package='robot_control', executable='ai_inference',
             name='ai_inference', output='screen'),

        # --- Dashboard bridge + camera ---
        ExecuteProcess(cmd=['ros2', 'launch', 'rosbridge_server',
                            'rosbridge_websocket_launch.xml'],
                       output='screen'),
        ExecuteProcess(cmd=['python3',
                            '/home/yvette_pi/ros2_ws/src/robot_control/robot_control/camera_stream.py'],
                       output='screen'),
    ])
