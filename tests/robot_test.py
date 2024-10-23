import pytest
import time
import math
from robot.robot import Robot


@pytest.fixture
def robot():
    return Robot()

def test_robot_init(robot):
    robot.reset()
    assert robot._speed == 0
    assert robot._acceleration == 2

def test_robot_move_to_coordinates(robot):
    robot.move_to_pickup_start()
    time.sleep(3)
    robot.get_state()
    assert math.isclose(math.degrees(robot._state['e']), 160, abs_tol=5)
    assert math.isclose(math.degrees(robot._state['b']), 0, abs_tol=5)
    assert math.isclose(math.degrees(robot._state['t']), 180, abs_tol=5)

