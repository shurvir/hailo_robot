import requests
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
                         'right':{'joint_letter': 'b', 'sign': -1, 'joint_index': 1},
                         'forward': {'joint_letter': 's', 'sign': +1, 'joint_index': 2},
                         'backward': {'joint_letter': 's', 'sign': -1, 'joint_index': 2}}
    
    ACTIONS = [ 'turn_left', 'turn_right', 'go_up', 'go_down', 'go_forward',
                'go_backward', 'light_on', 'light_off', 'look_around', 'pick_up_start', 
                'grab', 'reset', 'hold', 'release', 'throw']

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
        self.reset()

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
    
    def move_to_coordinates(self, x:int = None, y:int = None, z:int = None, t:int = None, speed:int = None, delay:float = 0):
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
        if speed is None:
            speed = self._speed
        command = f'{{"T":104,"x":{x},"y":{y},"z":{z},"t":{t},"spd":{speed}}}'
        self.do(command)
        time.sleep(delay)
    
    def move_to_position(self, e:int = None, b:int = None, s:int = None, h:int = None, speed:int = None, delay:float = 0):
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
        if speed is None:
            speed = self._speed
        command = f'{{"T":122,"b":{b},"s":{s},"e":{e},"h":{h},"spd":{speed},"acc":{self._acceleration}}}'
        self.do(command)
        time.sleep(delay)
        
    def exact_move(self, joint_index: int, degrees: int, delay: float = 0):
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

    def move(self, degrees: int, direction: str, delay: float = 0):
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
        self.exact_move(joint_index, adjusted_degrees, delay=delay)


    def move_left(self, degrees: int, delay: float = 0):
        """
            Moves the robot to the left.

            Args:
                degrees (int): The number of degrees to move.
                delay (int): The delay between commands.
        """
        self.move(degrees, 'left', delay=delay)

    def move_right(self, degrees: int, delay: float = 0):
        """
            Moves the robot to the right.

            Args:
                degrees (int): The number of degrees to move.
                delay (int): The delay between commands.
        """
        self.move(degrees, 'right', delay=delay)

    def move_up(self, degrees: int, delay: float = 0):
        """
            Moves the robot up.

            Args:
                degrees (int): The number of degrees to move.
                delay (int): The delay between commands.
        """
        self.move(degrees, 'up', delay=delay)

    def move_down(self, degrees: int, delay: float = 0):
        """
            Moves the robot down.

            Args:
                degrees (int): The number of degrees to move.
                delay (int): The delay between commands.
        """
        self.move(degrees, 'down', delay=delay)

    def move_forward(self, degrees: int, delay: float = 0):
        """
            Moves the robot forward.

            Args:
                delay (int): The delay between commands.
        """
        self.move(degrees, 'forward', delay=delay)

    def move_backward(self, degrees: int, delay:float = 0):
        """
            Moves the robot backward.

            Args:
                delay (int): The delay between commands.
        """
        self.move(degrees, 'backward', delay=delay)


    def set_light(self, intensity: int = 0):
        """
            Sets the light intensity of the robot.

            Args:
                intensity (int): The intensity of the light.
        """
        intensity = min(255, max(0, intensity))
        command = f'{{"T":114,"led":{intensity}}}'
        self.do(command)

    def hold(self):
        """
            Closes the robot grip
        """
        self.exact_move(4,220,delay=1)

    def grab(self):
        """
            Opens and then closes the the robot grip
        """
        self.exact_move(4,45,delay=5)
        self.exact_move(4,220,delay=1)

    def release(self):
        """
            Opens the robot grip
        """
        self.exact_move(4,90,delay=2)

    def look_around(self):
        """
            Moves the robot to look around
        """
        self.move_to_position(e=80,b=60,h=180,delay=4)
        self.move_to_position(e=80,b=-60,delay=10)
        self.move_to_position(e=120,b=-60,delay=4)
        self.move_to_position(e=120,b=60,delay=10)
        self.move_to_coordinates(x=250, y=0, z=250, delay=10)

    def move_to_coordinates_for_pickup(self, x: int, y: int, z:int):
        """
            moves the robot into position for pickup

            Args:
                x (int): The x coordinate.
                y (int): The y coordinate.
                z (int): The z coordinate.
        """
        y_offset = 10
        x_offset = 20
        self.move_to_coordinates(x=x/2, y=y, z=z+200, t=1.5, delay=4)
        if y < 0:
            self.move_to_coordinates(x=x+x_offset, y=y-y_offset, z=z, t=2, speed=1, delay=4)
        else:
            self.move_to_coordinates(x=x+x_offset, y=y-y_offset, z=z, t=2, speed=1, delay=4)
        self.hold()

    def throw(self):
        """
        {"T":122,"b":-90,"s":0,"e":145,"h":200,"spd":0,"acc":0}
        {"T":122,"b":0,"s":0,"e":90,"h":90,"spd":0,"acc":0}
        """
        self.move_to_position(e=145,b=-120,s=0,h=200,speed=0,delay=1)
        self.move_to_position(e=60,b=15,s=0,h=200,speed=0,delay=0.25)
        self.move_to_position(e=45,b=45,s=0,h=90,speed=0,delay=1)
        self.reset()

    def move_to_pick_up_start(self):
        """
            Moves the robot to the pickup start position
        """
        self.move_to_position(e=170,b=0,s=-40,delay=1)

    def do_action(self, action: str):
        """
            Performs an action on the robot.

            Args:
                action (str): The action to perform.
        """
        match action.lower():
            case '/turn_left':
                self.move_left(15)
            case '/turn_right':
                self.move_right(15)
            case '/go_up':
                self.move_up(15)
            case '/go_down':
                self.move_down(15)
            case '/go_forward':
                self.move_forward(15)
            case '/go_backward':
                self.move_backward(15)
            case '/light_on':
                self.set_light(255)
            case '/light_off':
                self.set_light(0)
            case '/look_around':
                self.look_around()
            case '/pick_up_start':
                self.move_to_pick_up_start()
            case '/grab':
                self.grab()
            case '/reset':
                self.reset()
            case '/hold':
                self.hold()
            case '/release':
                self.release()
            case '/throw':
                self.throw()
            case _:
                print('Invalid action')

def main():
    speed = 10
    acceleration = 10
    robot = Robot(speed=speed, acceleration=acceleration)
    time.sleep(1)
    robot.look_around()

if __name__ == "__main__":
    main()
