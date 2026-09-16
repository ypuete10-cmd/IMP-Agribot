from setuptools import find_packages, setup

package_name = 'robot_control'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='yvette_pi',
    maintainer_email='yvette_pi@todo.todo',
    description='Autonomous agricultural robot control package',
    license='MIT',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'motor_driver = robot_control.motor_driver:main',
            'camera_publisher = robot_control.camera_publisher:main',
            'capture_image = robot_control.capture:main',
            'camera_stream = robot_control.camera_stream:main',
        ],
    },
)
