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

_controller_tools = [
    {
        "name": "pick_up_object",
        "description": "Tells the robot to pick up the object input in the object_name parameter",
        "parameters": {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "description": "The name of the object to pick up."
                }
            },
            "required": ["object_name"]
        }
    },
    {
        "name": "find_object",
        "description": "Tells the robot to find the object input in the object_name parameter",
        "parameters": {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "description": "The name of the object to find."
                }
            },
            "required": ["object_name"]
        }
    },
    {
        "name": "get_scene",
        "description": "Returns a video of the scene",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {   "name": "describe_scene",
        "description": "Returns a description of the scene by passing the past 30 seconds of video to the AI chat bot.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {   "name": "get_camera_metadata",
        "description": "Returns the camera metadata",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {   "name": "get_camera_image",
        "description": "Returns an image from the camera",
        "parameters": {
            "type": "object",
            "properties": {},
        }
    },
    {   "name": "drop_off_object",
        "description": "Tells the robot to drop off the object",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The location to drop off the object (left, right, behind).",
                    "enum": ["left", "right", "behind"]
                }
            },
            "required": ["location"]
        }
    },
    {
        "name": "track",
        "description": "Tells the robot to track the object input in the object_name parameter",
        "parameters": {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "description": "The name of the object to track."
                },
                "object_id": {
                    "type": "string",
                    "description": "The ID of the object to track."
                }
            },
            "required": ["object_name", "object_id"]
        }
    },
    {
        "name": "send_action_to_robot",
        "description": "Sends an action to the robot",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The action to send to the robot.",
                    "enum": Robot.get_actions()
                }
            },
            "required": ["message"]
        }
    },
]

def pick_up_object(object_name: str):
    """
        Tells the robot to pick up the object input in the object_name parameter

        Args: 
            object_name (str): The name of the object to pick up.
    """
    camera_metadata = camera_queue.get()
    coordinates = camera_processor.get_coordinates_of_object(object_name, camera_metadata['detections'])
    print(coordinates)
    if coordinates is not None:
        hailo_bot.move_to_coordinates_for_pickup(x=coordinates[0], y=coordinates[1], z=coordinates[2])

def drop_off_object(location: str):
    """
        Tells the robot to drop off the object
    """
    hailo_bot.move_up(90,delay=3)
    if location.lower() == 'left':
        hailo_bot.move_to_coordinates(x=-100, y=600, z=200, delay=5)
    elif location.lower() == 'right':
        hailo_bot.move_to_coordinates(x=-100, y=-600, z=200, delay=5)
    elif location.lower() == 'behind':
        hailo_bot.move_to_coordinates(x=-600, y=0, z=200, delay=8)
    
    hailo_bot.release()
    hailo_bot.move_to_pick_up_start()
    hailo_bot.hold()

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


def find_object(object_name: str, telegram_bot: telebot.TeleBot, chat_id: int):
    """
        Tell the AI bot to identify an object on the camera and send a photo to the telegram chat

        Args: 
            object_name (str): The name of the object to find.
    """
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
        telegram_bot.send_message(chat_id, "Object not found")
        return
    else:
        # move robot to coordinates
        relative_x, relative_y = camera_utils.get_robot_position_from_bbox((x1, y1, x2, y2), camera_processor.camera_width, camera_processor.camera_height)
        hailo_bot.move_to_relative_position(b=relative_x, e=relative_y)

        # draw square on image with label
        labeled_image = camera_utils.draw_square_on_image(camera_metadata, (x1, y1, x2, y2), label_name)
        labeled_image_bytes = camera_utils.convert_array_image_cv2(labeled_image, 'PNG')
        telegram_bot.send_photo(chat_id, photo=labeled_image_bytes)

def get_camera_metadata(telegram_bot: telebot.TeleBot, chat_id: int):
    """
        Returns the camera metadata
    """
    if camera_queue is not None:
        camera_metadata = camera_queue.get()['image']
        img_byte_arr, img = camera_utils.convert_array_image(camera_metadata, 'PNG')
        
        # Get VN response
        description = ai_chat_bot.generate_content(prompt="Describe this image.", data=img)

        telegram_bot.send_photo(chat_id, photo=img_byte_arr)
        telegram_bot.send_message(chat_id, description)

def get_camera_image(telegram_bot: telebot.TeleBot, chat_id: int):
    """
        Returns an image from the camera
    """
    if camera_queue is not None:
        camera_metadata = camera_queue.get()['image']
        img_byte_arr, img = camera_utils.convert_array_image(camera_metadata, 'PNG')
        telegram_bot.send_photo(chat_id, photo=img_byte_arr)

def get_scene(telegram_bot: telebot.TeleBot, chat_id: int):
    """
        Returns a video of the scene
    """
    if video_queue is not None:
        image_array = []
        while not video_queue.empty():
            image_array.append(video_queue.get()['image'])
        
        video_data = camera_utils.create_mp4_from_images(image_array)
        video_data.seek(0)

        if video_data is not None:
            telegram_bot.send_video(chat_id=chat_id, video=video_data)

def describe_scene(telegram_bot: telebot.TeleBot, chat_id: int):
    """
        Returns a description of the scene by passing the past 30 seconds of video to the AI chat bot.
    """
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
        if video_data is not None:
            telegram_bot.send_video(chat_id=chat_id, video=video_data)
            telegram_bot.send_message(chat_id, description)
            ai_chat_bot.send_message(description)
    
def send_message_to_AI(message: str, telegram_bot: telebot.TeleBot, chat_id: int):
    """
        Sends a message to the AI chat bot and returns the response
    
        Args: 
            message (str): The message to send to the AI chat bot.
    """
    response = ai_chat_bot.send_message(message)
    output_message = response.text
    
    # execute any function calls in the response
    if response.function_calls is not None:
        output_message = ''
        for function_call in response.function_calls:
            func_name = function_call.name
            args = function_call.args
            
            # Get the function from the current script's globals
            func = globals().get(func_name)

            if func:
                # Create a copy of args to avoid modifying the original
                execution_args = dict(args)
                
                # Add telegram_bot and chat_id to execution args if the function needs them
                sig = inspect.signature(func)
                if 'telegram_bot' in sig.parameters:
                    execution_args['telegram_bot'] = telegram_bot
                if 'chat_id' in sig.parameters:
                    execution_args['chat_id'] = chat_id
                
                # Execute the function
                try:
                    # We don't capture the return value for now, just execute
                    print(f"Executing function: {func_name} with args: {execution_args}")
                    func(**execution_args)
                    output_message += f"Executed function: {func_name}"
                except Exception as e:
                    output_message += f"Error executing function {func_name}: {e}"
            else:
                # Fallback for functions not found (using original args for display)
                args_str = ", ".join(f"{key}={val}" for key, val in args.items())
                output_message += f"Function call: {func_name}({args_str})"

    telegram_bot.send_message(chat_id, output_message)
    asyncio.run(say(output_message.replace('*','')))

def map_instruction_to_action(instruction: str, telegram_bot: telebot.TeleBot, chat_id: int):
    """
        Maps an instruction to an action
    
        Args: 
            instruction (str): The instruction to map to an action.
    """

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
        describe_scene(telegram_bot, chat_id)
        return 'describe scene'
    elif command_string == 'get_camera_metadata':
        get_camera_metadata(telegram_bot, chat_id)
        return 'get camera metadata'
    elif command_string.startswith('find') and len(list_of_commands) > 1:
        find_object((' '.join(list_of_commands[1:])).strip('.'), telegram_bot, chat_id)
        return 'find object'
    else:
        return None

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

def send_action_to_robot(message):
    """
        Sends an action to the robot
    
        Args: 
            message (str): The action to send to the robot.
    """
    hailo_bot.do_action(message)

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

def track(object_name, object_id):
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

BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)
hailo_bot = Robot(speed=20, acceleration=10)
ROBOT_COMMANDS = Robot.get_actions()
controller_tools = [types.Tool(function_declarations=_controller_tools)]
ai_chat_bot: ai_chat.AIChat = ai_chat.GeminiChat(controller_tools)
camera_queue = None
video_queue = None
tracking = False