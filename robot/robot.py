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
    
    def move_to_coordinates(self, x:int = None, y:int = None, z:int = None, t:int = None, delay:int = 0):
        """
            Moves the robot to a specific position.

            Args:
                x (int): The value of joint x.
                y (int): The value of joint y.
                z (int): The value of joint z.
                t (int): The value of joint t.
                delay (int): The delay between commands.
            
            Returns:
                None
        """
        self._state = self.get_state()
        if x is None:
            x = self._state['x']
        if y is None:
            y = self._state['y']
        if z is None:
            z = self._state['z']
        if t is None:
            t = self._state['t']
        command = f'{{"T":104,"x":{x},"y":{y},"z":{z},"t":{t},"spd":{self._speed}}}'
        self.do(command)
        time.sleep(delay)
    
    def move_to_position(self, e:int = None, b:int = None, s:int = None, h:int = None, delay:int = 0):
        """
            Moves the robot to a specific position.

            Args:
                e (int): The value of joint e.
                b (int): The value of joint b.
                s (int): The value of joint s.
                h (int): The value of joint h.
                delay (int): The delay between commands.
            
            Returns:
                None
        """
        self._state = self.get_state()
        if e is None:
            e = math.degrees(self._state['e'])
        if b is None:
            b = math.degrees(self._state['b'])
        if s is None:
            s = math.degrees(self._state['s'])
        if h is None:
            h = math.degrees(self._state['t'])
        command = f'{{"T":122,"b":{b},"s":{s},"e":{e},"h":{h},"spd":{self._speed},"acc":{self._acceleration}}}'
        self.do(command)
        time.sleep(delay)
        
    def exact_move(self, joint_index: int, degrees: int, delay: int = 0):
        """
            Moves the robot to a specific position.

            Args:
                joint_index (int): The index of the joint to move.
                degrees (int): The number of degrees to move.
                delay (int): The delay between commands.
            
            Returns:
                None
        """
        command = f'{{"T":121,"joint":{joint_index},"angle":{degrees},"spd":{self._speed},"acc":{self._acceleration}}}'
        self.do(command)
        time.sleep(delay)

    def move(self, degrees: int, direction: str, delay: int = 0):
        """
            Moves the robot in a specific direction.

            Args:
                degrees (int): The number of degrees to move.
                direction (str): The direction to move.
                delay (int): The delay between commands.

            Returns:
                None
        """
        joint = self._directions[direction]['joint_letter']
        sign = self._directions[direction]['sign']
        joint_index = self._directions[direction]['joint_index']
        self._state = self.get_state()
        adjusted_degrees = math.degrees(self._state[joint]) + sign * degrees
        self.exact_move(joint_index, adjusted_degrees, direction, delay=delay)


    def move_left(self, degrees: int, delay: int = 0):
        """
            Moves the robot to the left.

            Args:
                degrees (int): The number of degrees to move.
                delay (int): The delay between commands.
        """
        self.move(degrees, 'left', delay=delay)

    def move_right(self, degrees: int, delay: int = 0):
        """
            Moves the robot to the right.

            Args:
                degrees (int): The number of degrees to move.
                delay (int): The delay between commands.
        """
        self.move(degrees, 'right', delay=delay)

    def move_up(self, degrees: int, delay: int = 0):
        """
            Moves the robot up.

            Args:
                degrees (int): The number of degrees to move.
                delay (int): The delay between commands.
        """
        self.move(degrees, 'up', delay=delay)

    def move_down(self, degrees: int, delay: int = 0):
        """
            Moves the robot down.

            Args:
                degrees (int): The number of degrees to move.
                delay (int): The delay between commands.
        """
        self.move(degrees, 'down', delay=delay)

    def set_light(self, intensity: int = 0):
        """
            Sets the light intensity of the robot.

            Args:
                intensity (int): The intensity of the light.
        """
        intensity = min(255, max(0, intensity))
        command = f'{{"T":114,"led":{intensity}}}'
        self.do(command)


def main():
    speed = 10
    acceleration = 10
    robot = Robot(speed=speed, acceleration=acceleration)
    robot.reset()
    time.sleep(2)
    for i in range(5):
        robot.set_light(100)
        robot.move_to_position(e=60,b=90,h=180,delay=6)
        robot.set_light(0)
        robot.move_to_position(e=60,b=-90,delay=16)
        robot.move_to_position(e=115,b=-90,delay=6)
        robot.move_to_position(e=115,b=90,delay=16)
        robot.set_light(100)
        robot.move_to_coordinates(x=250, y=0, z=250, delay=10)
        robot.set_light(0)

if __name__ == "__main__":
    main()
