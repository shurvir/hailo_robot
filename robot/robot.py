import requests
import argparse
import math
import json
import time

ROARM_IP = '192.168.182.245' # Static IP for now but need to figure out how to get this dynamic

class Robot():
    """
        Represents a robot arm.
    
        Attributes:
            _ip_addr (str): The IP address of the robot.
            _state (dict): The current state of the robot.
            _speed (int): The speed of the robot.
            _acceleration (int): The acceleration of the robot.
            _delay (int): The delay between commands.
            _directions (dict): A dictionary of directions.
    """
    _ip_addr: str
    _state: dict
    _speed: int
    _acceleration: int
    _directions: dict = {'up':   {'joint_letter': 'e', 'sign': -1, 'joint_index': 3},
                         'down': {'joint_letter': 'e', 'sign': +1, 'joint_index': 3},
                         'left': {'joint_letter': 'b', 'sign': +1, 'joint_index': 1},
                         'right':{'joint_letter': 'b', 'sign': -1, 'joint_index': 1}}

    def __init__(self, speed: int = 0, acceleration: int = 2) -> None:
        """
            Initializes a new instance of the Robot class.

            Args:
                speed (int): The speed of the robot.
                acceleration (int): The acceleration of the robot.
                delay (int): The delay between commands.
        """
        self._ip_addr = ROARM_IP
        self._state = self.get_state()
        self._speed = speed
        self._acceleration = acceleration

    def reset(self):
        """
            Resets the robot to its initial state.
        """
        self.do('{"T":100}')

    def get_state(self):
        """
            Returns the current state of the robot.

            Returns:
                dict: The current state of the robot.
        """
        return json.loads(self.do('{"T":105}'))

    def do(self, command: str):
        """
            Sends a command to the robot and returns the response.

            Args:
                command (str): The command to send to the robot.

            Returns:
                str: The response from the robot.
        """
        url = "http://" + self._ip_addr + "/js?json=" + command
        response = requests.get(url)
        content = response.text
        return content
    
    def move(self, degrees: int, direction: str, delay: int = 0):
        """
            Moves the robot in a specified direction.

            Args:
                degrees (int): The number of degrees to move.
                direction (str): The direction to move.
        """
        joint = self._directions[direction]['joint_letter']
        sign = self._directions[direction]['sign']
        joint_index = self._directions[direction]['joint_index']
        self._state = self.get_state()
        adjusted_degrees = math.degrees(self._state[joint]) + sign * degrees
        command = f'{{"T":121,"joint":{joint_index},"angle":{adjusted_degrees},"spd":{self._speed},"acc":{self._acceleration}}}'
        self.do(command)
        time.sleep(delay)

    def move_left(self, degrees: int, delay: int = 0):
        """
            Moves the robot to the left.

            Args:
                degrees (int): The number of degrees to move.
        """
        self.move(degrees, 'left', delay=delay)

    def move_right(self, degrees: int, delay: int = 0):
        """
            Moves the robot to the right.

            Args:
                degrees (int): The number of degrees to move.
        """
        self.move(degrees, 'right', delay=delay)

    def move_up(self, degrees: int, delay: int = 0):
        """
            Moves the robot up.

            Args:
                degrees (int): The number of degrees to move.
        """
        self.move(degrees, 'up', delay=delay)

    def move_down(self, degrees: int, delay: int = 0):
        """
            Moves the robot down.

            Args:
                degrees (int): The number of degrees to move.
        """
        self.move(degrees, 'down', delay=delay)

def main():
    robot = Robot()
    while True:
        robot.move_left(30, delay=0)
        robot.move_down(10, delay=1)
        robot.move_right(60, delay=0)
        robot.move_up(10, delay=1)
        robot.reset()

if __name__ == "__main__":
    main()
