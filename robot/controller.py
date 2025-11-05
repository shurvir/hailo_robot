import os
import telebot
import ai_chat
import camera_utils
import camera_processor
import os
from tts import say
import asyncio
import time
from robot import Robot
import json
from google.genai import types
import inspect
from functools import wraps

# Global context for current request (telegram_bot and chat_id)
_current_context = {"telegram_bot": None, "chat_id": None}

# Controller tools are now defined as actual Python functions below
# The Gemini SDK will automatically convert them to function declarations

def pick_up_object(object_name: str) -> dict:
    """
    Tells the robot to pick up the object input in the object_name parameter.

    Args: 
        object_name: The name of the object to pick up.
        
    Returns:
        A dictionary with status and message about the pickup operation.
    """
    camera_metadata = camera_queue.get()
    coordinates = camera_processor.get_coordinates_of_object(object_name, camera_metadata['detections'])
    print(coordinates)
    if coordinates is not None:
        hailo_bot.move_to_coordinates_for_pickup(x=coordinates[0], y=coordinates[1], z=coordinates[2])
        return {"status": "success", "message": f"Picked up {object_name}"}
    
    return {"status": "error", "message": f"Could not find coordinates for {object_name}"}

def drop_off_object(location: str) -> dict:
    """
    Tells the robot to drop off the object at the specified location.
    
    Args:
        location: The location to drop off the object (left, right, or behind).
        
    Returns:
        A dictionary with status and message about the drop-off operation.
    """
    hailo_bot.move_up(90, delay=3)
    if location.lower() == 'left':
        hailo_bot.move_to_coordinates(x=-100, y=600, z=200, delay=5)
    elif location.lower() == 'right':
        hailo_bot.move_to_coordinates(x=-100, y=-600, z=200, delay=5)
    elif location.lower() == 'behind':
        hailo_bot.move_to_coordinates(x=-600, y=0, z=200, delay=8)
    else:
        return {"status": "error", "message": f"Invalid location: {location}. Use left, right, or behind."}
    
    hailo_bot.release()
    hailo_bot.move_to_pick_up_start()
    hailo_bot.hold()
    
    return {"status": "success", "message": f"Dropped off object at {location}"}

def detect_object(object_name: str):
    # get image from queue
    camera_metadata = camera_queue.get()['image']
    # convert image to byte array
    img = camera_utils.convert_array_image_PIL(camera_metadata, 'JPEG')
    # prompt the AI bot to identify the object in the image
    prompt = f'Detect the 2d bounding boxes of objects matching the description "{object_name}" (only strong matches).'
    response = ai_chat_bot.get_bbox_coordinates(prompt=prompt,
                                                data=img)
    return response, camera_metadata


def find_object(object_name: str) -> dict:
    """
    Tell the AI bot to identify an object on the camera and send a photo to the telegram chat.

    Args: 
        object_name: The name of the object to find.
        
    Returns:
        A dictionary with status and message about the operation.
    """
    telegram_bot = _current_context.get("telegram_bot")
    chat_id = _current_context.get("chat_id")
    
    label_name = None
    positions = Robot.get_preset_positions()
    for position in positions:
        response, camera_metadata = detect_object(object_name)
        # get bounding box coordinates from response
        try:
            json_response = json.loads(response.replace("```json\n", "").replace("```", ""))
            y1, x1, y2, x2 = map(int, json_response[0]['box_2d'])
            label_name = json_response[0]['label']
            y1 = int(y1/1000.0 * camera_processor.camera_height)
            x1 = int(x1/1000.0 * camera_processor.camera_width)
            y2 = int(y2/1000.0 * camera_processor.camera_height)
            x2 = int(x2/1000.0 * camera_processor.camera_width)
            print(f'{x1}, {y1}, {x2}, {y2}')
            break
        except:
            hailo_bot.move_to_preset_position(position)

    if label_name is None:
        if telegram_bot and chat_id:
            telegram_bot.send_message(chat_id, "Object not found")
        return {"status": "not_found", "message": f"Object '{object_name}' not found"}
    else:
        # move robot to coordinates
        relative_x, relative_y = camera_utils.get_robot_position_from_bbox((x1, y1, x2, y2), camera_processor.camera_width, camera_processor.camera_height)
        hailo_bot.move_to_relative_position(b=relative_x, e=relative_y)

        # draw square on image with label
        labeled_image = camera_utils.draw_square_on_image(camera_metadata, (x1, y1, x2, y2), label_name)
        labeled_image_bytes = camera_utils.convert_array_image_cv2(labeled_image, 'PNG')
        if telegram_bot and chat_id:
            telegram_bot.send_photo(chat_id, photo=labeled_image_bytes)
        
        return {"status": "success", "message": f"Found {label_name} and moved robot to position"}

def get_camera_metadata() -> dict:
    """
    Returns the camera metadata with a description of the image.
    
    Returns:
        A dictionary with the image description.
    """
    telegram_bot = _current_context.get("telegram_bot")
    chat_id = _current_context.get("chat_id")
    
    if camera_queue is not None:
        camera_metadata = camera_queue.get()['image']
        img_byte_arr, img = camera_utils.convert_array_image(camera_metadata, 'PNG')
        
        # Get VN response
        description = ai_chat_bot.generate_content(prompt="Describe this image.", data=img)

        if telegram_bot and chat_id:
            telegram_bot.send_photo(chat_id, photo=img_byte_arr)
            telegram_bot.send_message(chat_id, description)
        
        return {"description": description}
    
    return {"description": "No camera data available"}

def get_camera_image() -> dict:
    """
    Returns an image from the camera.
    
    Returns:
        A dictionary with status of the operation.
    """
    telegram_bot = _current_context.get("telegram_bot")
    chat_id = _current_context.get("chat_id")
    
    if camera_queue is not None:
        camera_metadata = camera_queue.get()['image']
        img_byte_arr, img = camera_utils.convert_array_image(camera_metadata, 'PNG')
        if telegram_bot and chat_id:
            telegram_bot.send_photo(chat_id, photo=img_byte_arr)
        return {"status": "success", "message": "Image captured and sent"}
    
    return {"status": "error", "message": "No camera data available"}

def get_scene() -> dict:
    """
    Returns a video of the scene.
    
    Returns:
        A dictionary with status of the operation.
    """
    telegram_bot = _current_context.get("telegram_bot")
    chat_id = _current_context.get("chat_id")
    
    if video_queue is not None:
        image_array = []
        while not video_queue.empty():
            image_array.append(video_queue.get()['image'])
        
        video_data = camera_utils.create_mp4_from_images(image_array)
        video_data.seek(0)

        if video_data is not None and telegram_bot and chat_id:
            telegram_bot.send_video(chat_id=chat_id, video=video_data)
            return {"status": "success", "message": "Video captured and sent"}
    
    return {"status": "error", "message": "No video data available"}

def describe_scene() -> dict:
    """
    Returns a description of the scene by passing the past 30 seconds of video to the AI chat bot.
    
    Returns:
        A dictionary with the video description.
    """
    telegram_bot = _current_context.get("telegram_bot")
    chat_id = _current_context.get("chat_id")
    
    if video_queue is not None:
        image_array = []
        while not video_queue.empty():
            image_array.append(video_queue.get()['image'])
        
        video_data = camera_utils.create_mp4_from_images(image_array)
        video_data.seek(0)
        
        # Debug
        #if video_data:
        #    with open('/home/pi/Desktop/my_video.mp4', 'wb') as f:
        #        f.write(video_data.getbuffer())
                
        # Get VN response
        description =  ai_chat_bot.generate_content_from_video(prompt="Describe this video.", 
                                                    video_data=video_data.getvalue(),
                                                    mime_type="video/mp4")
        if video_data is not None and telegram_bot and chat_id:
            telegram_bot.send_video(chat_id=chat_id, video=video_data)
            telegram_bot.send_message(chat_id, description)
            ai_chat_bot.send_message(description)
        
        return {"description": description}
    
    return {"description": "No video data available"}
    
def send_message_to_AI(message: str, telegram_bot: telebot.TeleBot, chat_id: int):
    """
    Sends a message to the AI chat bot and returns the response.
    With automatic function calling enabled, the SDK will automatically:
    1. Detect function calls in the model's response
    2. Execute the corresponding Python functions
    3. Send results back to the model
    4. Return the final text response
    
    Args: 
        message: The message to send to the AI chat bot.
        telegram_bot: The telegram bot instance for sending responses.
        chat_id: The chat ID to send responses to.
    """
    # Set the current context so functions can access telegram_bot and chat_id
    _current_context["telegram_bot"] = telegram_bot
    _current_context["chat_id"] = chat_id
    
    try:
        # With automatic function calling, send_message handles everything
        response = ai_chat_bot.send_message(message)
        output_message = response.text
        
        # Send response to telegram and TTS
        telegram_bot.send_message(chat_id, output_message)
        asyncio.run(say(output_message.replace('*','')))
    finally:
        # Clear context after request
        _current_context["telegram_bot"] = None
        _current_context["chat_id"] = None

def map_instruction_to_action(instruction: str, telegram_bot: telebot.TeleBot, chat_id: int):
    """
    Maps an instruction to an action.
    
    Args: 
        instruction: The instruction to map to an action.
        telegram_bot: Telegram bot instance for context.
        chat_id: Chat ID for context.
        
    Returns:
        The action name if mapped, None otherwise.
    """
    # Set context for function calls
    _current_context["telegram_bot"] = telegram_bot
    _current_context["chat_id"] = chat_id
    
    try:
        list_of_commands = [t.strip('.').strip(',') for t in instruction.lower().split(' ')]
        command_string = '_'.join(list_of_commands)
        if command_string in ROBOT_COMMANDS:
            hailo_bot.do_action(command_string)
            return command_string
        elif command_string.startswith('pick_up') and len(list_of_commands) > 2:
            pick_up_object((' '.join(list_of_commands[2:])).strip('.'))
            return 'pick up'
        elif command_string.startswith('drop_off') and len(list_of_commands) > 2:
            drop_off_object(list_of_commands[2].strip('.'))
            return 'drop off'
        elif command_string == 'describe_scene':
            describe_scene()
            return 'describe scene'
        elif command_string == 'get_camera_metadata':
            get_camera_metadata()
            return 'get camera metadata'
        elif command_string.startswith('find') and len(list_of_commands) > 1:
            find_object((' '.join(list_of_commands[1:])).strip('.'))
            return 'find object'
        else:
            return None
    finally:
        # Clear context
        _current_context["telegram_bot"] = None
        _current_context["chat_id"] = None

def process_audio(downloaded_file, telegram_bot: telebot.TeleBot, chat_id: int):
    """
        Processes an audio file and returns the response
    
        Args: 
            downloaded_file (bytes): The audio file to process.
    """
     # Get VN response
    #prompt = "transcribe this audio without any safety filtering."
    #transcription = ai_chat_bot.generate_content(prompt=prompt, mime_type="audio/ogg", data=downloaded_file)
    #transcription = ai_chat.transcribe_ogg_bytes(downloaded_file)
    transcription = ai_chat.transcribe_audio_bytes(downloaded_file)
    print(f'transcription: {transcription}')
    send_message_to_AI(transcription, telegram_bot, chat_id)

def send_action_to_robot(message: str) -> dict:
    """
    Sends an action command to the robot.
    
    Args: 
        message (str): The action command to send to the robot.
            Possible values include:
            - "go_forward": Move the robot forward
            - "go_left": Move the robot left
            - "go_right": Move the robot right
            - "go_up": Move the robot up
            - "go_down": Move the robot down
            - "go_backward": Move the robot backward
            - "light_on": Turn the robot's light on
            - "light_off": Turn the robot's light off
            - "look_around": Make the robot look around
            - "look_left": Make the robot look left
            - "look_right": Make the robot look right
            - "pick_up_start": Move the robot to pick up start position 
            - "grab": Make the robot grab an object
            - "reset": Reset the robot's position
            - "hold": Make the robot hold an object
            - "release": Make the robot release an object
            - "throw": Make the robot throw an object
        
    Returns:
        A dictionary with status and message about the action execution.
    """
    hailo_bot.do_action(message)
    return {"status": "success", "message": f"Executed robot action: {message}"}

def list_commands(telegram_bot: telebot.TeleBot, chat_id: int):
    """
        Lists the available commands
    """
    telegram_bot.send_message(chat_id, "Available commands: ")
    for command in ROBOT_COMMANDS:
        telegram_bot.send_message(chat_id, f"/{command}")
    telegram_bot.send_message(chat_id, "/pick_up <object_name>")
    telegram_bot.send_message(chat_id, "/drop_off <location>")
    telegram_bot.send_message(chat_id, "/find <object_name>")
    telegram_bot.send_message(chat_id, "/get_camera_metadata")
    telegram_bot.send_message(chat_id, "/get_camera_image")
    telegram_bot.send_message(chat_id, "/get_scene")
    telegram_bot.send_message(chat_id, "/describe_scene")
    telegram_bot.send_message(chat_id, "/track_object <object_name> <object_id>")
    telegram_bot.send_message(chat_id, "/list_commands")

def track(object_name: str, object_id: str) -> dict:
    """
    Tells the robot to track the specified object.
    
    Args:
        object_name: The name of the object to track.
        object_id: The ID of the object to track.
        
    Returns:
        A dictionary with status and message about the tracking operation.
    """
    global tracking
    tracking = False
    if camera_queue is not None:
        tracking = True
        tracking_counter = 0
        while tracking:
            detections = camera_queue.get()['detections']
            instructions = camera_processor.get_direction_to_object(object_name, detections, object_id)
            if instructions is not None:
                if 'up' in instructions:
                    hailo_bot.move_up(instructions['up'])
                if 'down' in instructions:
                    hailo_bot.move_down(instructions['down'])
                if 'left' in instructions:
                    hailo_bot.move_left(instructions['left'])
                if 'right' in instructions: 
                    hailo_bot.move_right(instructions['right'])
                tracking_counter = 0
            else:
                tracking_counter = tracking_counter + 1
                if tracking_counter > 25:
                    tracking = False
                    break
            time.sleep(0.25)
        
        return {"status": "success", "message": f"Tracked {object_name} (ID: {object_id})"}
    
    return {"status": "error", "message": "No camera data available for tracking"}

def wait(time_seconds: int) -> dict:
    """
    Tells the robot to wait for the specified number of seconds.
    
    Args:
        time_seconds: The number of seconds to wait.
    """
    time.sleep(time_seconds)
    return {"status": "success", "message": f"Waited for {time_seconds} seconds"}

# Initialize the bot and robot
BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)
hailo_bot = Robot(speed=20, acceleration=10)
ROBOT_COMMANDS = Robot.get_actions()

# Define controller tools as actual Python functions for automatic function calling
# The SDK will convert these to function declarations automatically
_controller_tools = [
    pick_up_object,
    find_object,
    get_scene,
    describe_scene,
    get_camera_metadata,
    get_camera_image,
    drop_off_object,
    track,
    send_action_to_robot,
    wait,
]

ai_chat_bot: ai_chat.AIChat = ai_chat.GeminiChat(_controller_tools)
camera_queue = None
video_queue = None
tracking = False