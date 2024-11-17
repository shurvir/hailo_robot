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

BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)
hailo_bot = Robot(speed=20, acceleration=10)
ROBOT_COMMANDS = hailo_bot.get_commands()
ai_chat_bot: ai_chat.AIChat = ai_chat.GeminiChat()
camera_queue = None
video_queue = None
tracking = False

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


def find_object(object_name: str):
    """
        Tell the AI bot to identify an object on the camera and pick up that object

        Args: 
            object_name (str): The name of the object to find.
    """
    camera_metadata = camera_queue.get()['image']
    image_byte_arr, _ = camera_utils.convert_array_image(camera_metadata, 'PNG')
    prompt = f'What are the bounding box coordinates of the {object_name} in this image?'+ \
        ' Given that the image is 1280x1280, return the coordinates in the form x1, y1, x2, y2.'
    response = ai_chat_bot.generate_content(prompt=prompt,
                                            mime_type='image/png', data=image_byte_arr.getvalue())
    y1, x1, y2, x2 = map(int, response.split(',')[0:4])
    coordinates = camera_utils.get_robot_coordinates_from_bbox((x1, y1, x2, y2))
    camera_utils.save_temp_image(camera_utils.draw_square_on_image(camera_metadata, (x1, y1, x2, y2)))
    if coordinates is not None:
        hailo_bot.move_to_coordinates(x=coordinates[0], y=coordinates[1], z=coordinates[2], t=1.5)

def get_camera_metadata(telegram_bot: telebot.TeleBot, chat_id: int):
    """
        Returns the camera metadata
    """
    if camera_queue is not None:
        camera_metadata = camera_queue.get()['image']
        img_byte_arr, img = camera_utils.convert_array_image(camera_metadata, 'PNG')
        
        # Get VN response
        ai_chat_bot.send_message(img)
        description = ai_chat_bot.send_message("Describe this image.")

        telegram_bot.send_photo(chat_id, photo=img_byte_arr)
        telegram_bot.send_message(chat_id, description)

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
                                                    video_data=video_data.getvalue())
        if video_data is not None:
            telegram_bot.send_video(chat_id=chat_id, video=video_data)
            telegram_bot.send_message(chat_id, description)
    
def send_message_to_AI(message: str, telegram_bot: telebot.TeleBot, chat_id: int):
    """
        Sends a message to the AI chat bot and returns the response
    
        Args: 
            message (str): The message to send to the AI chat bot.
    """
    response = ai_chat_bot.send_message(message)
    telegram_bot.send_message(chat_id, response)
    asyncio.run(say(response.replace('*','')))

def map_instruction_to_action(instruction: str, telegram_bot: telebot.TeleBot, chat_id: int):
    """
        Maps an instruction to an action
    
        Args: 
            instruction (str): The instruction to map to an action.
    """

    list_of_commands = [t.strip('.').strip(',') for t in instruction.lower().split(' ')]
    command_string = '_'.join(list_of_commands)
    if command_string in ROBOT_COMMANDS:
        hailo_bot.do_action('/'+ command_string)
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

    if map_instruction_to_action(transcription, telegram_bot, chat_id) is None:
        # Respond
        response = ai_chat_bot.send_message(transcription)
        # Send response to the chat
        telegram_bot.send_message(chat_id, response)
        asyncio.run(say(response.replace('*','')))

def send_action_to_robot(message):
    """
        Sends an action to the robot
    
        Args: 
            message (str): The action to send to the robot.
    """
    hailo_bot.do_action(message)

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