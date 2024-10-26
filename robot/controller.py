import os
import telebot
import io
import ai_chat
import camera_utils
import camera_processor
import os
from tts import say
import asyncio
from robot import Robot
from PIL import Image
import cv2

BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN')
ROBOT_COMMANDS = Robot.ACTIONS
bot = telebot.TeleBot(BOT_TOKEN)
hailo_bot = Robot(speed=20, acceleration=10)
ai_chat_bot: ai_chat.AIChat = ai_chat.GeminiChat()
camera_queue = None

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

def get_camera_metadata():
    """
        Returns the camera metadata
    """
    if camera_queue is not None:
        camera_metadata = camera_queue.get()['image']
        img_byte_arr, img = camera_utils.convert_array_image(camera_metadata, 'PNG')
        
        # Get VN response
        ai_chat_bot.send_message(img)
        description = ai_chat_bot.send_message("Describe this image.")

        return img_byte_arr, description
    else:
        return None, None

def describe_scene():
    """
        Returns a description of the scene by passing the past 30 seconds of video to the AI chat bot.
    """
    if camera_queue is not None:
        image_array = []
        while not camera_queue.empty():
            image_array.insert(0, camera_queue.get()['image'])
        
        video_data = camera_utils.create_mp4_from_images(image_array)
        video_data.seek(0)
        
        # Debug
        #if video_data:
        #    with open('/home/pi/Desktop/my_video.mp4', 'wb') as f:
        #        f.write(video_data.getbuffer())
                
        video_data.seek(0)
        # Get VN response
        description =  ai_chat_bot.generate_content_from_video(prompt="Describe this video.", 
                                                    video_data=video_data.getvalue())
        return video_data, description
    else:
        return None, None
    
def send_message_to_AI(message):
    """
        Sends a message to the AI chat bot and returns the response
    
        Args: 
            message (str): The message to send to the AI chat bot.

        Returns:
            str: The response from the AI chat bot.
    """
    response = ai_chat_bot.send_message(message)
    asyncio.run(say(response.replace('*','')))

    return response

def process_audio(downloaded_file):
    """
        Processes an audio file and returns the response
    
        Args: 
            downloaded_file (bytes): The audio file to process.

        Returns:
            str: The response from the AI chat bot.
    """
     # Get VN response
    prompt = "Transcribe this audio."
    transcription = ai_chat_bot.generate_content(prompt=prompt, mime_type="audio/ogg", data=downloaded_file)

    # Respond
    response = ai_chat_bot.send_message(transcription)
    asyncio.run(say(response.replace('*','')))

    return response

def send_action_to_robot(message):
    """
        Sends an action to the robot
    
        Args: 
            message (str): The action to send to the robot.
    """
    hailo_bot.do_action(message)