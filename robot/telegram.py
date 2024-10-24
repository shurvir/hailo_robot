import os
import telebot
import io
import ai_chat
import video_utils
import camera_processor
import os
from tts import say
import asyncio
from robot import Robot
from PIL import Image

BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN')
ROBOT_COMMANDS = Robot.ACTIONS
bot = telebot.TeleBot(BOT_TOKEN)
hailo_bot = Robot(speed=10, acceleration=10)
ai_chat_bot: ai_chat.AIChat = ai_chat.GeminiChat()
camera_queue = None

@bot.message_handler(commands=['go_to'])
def go_to(message):
    camera_metadata = camera_queue.get()
    object_name = message.text.replace('/go_to','').strip()
    coordinates = camera_processor.get_coordinates_of_object(object_name, camera_metadata['detections'])
    print(coordinates)
    if coordinates is not None:
        hailo_bot.move_to_coordinates(x=coordinates[0], y=coordinates[1], z=coordinates[2], t=2)

@bot.message_handler(commands=ROBOT_COMMANDS)
def do_robot_action(message):
    hailo_bot.do_action(message.text)

@bot.message_handler(commands=['get_camera_metadata'])
def send_camera_metadata(message):
    if camera_queue is not None:
        camera_metadata = camera_queue.get()['image']
        img = Image.fromarray(camera_metadata)
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')  # or 'JPEG'
        img_byte_arr.seek(0)
        
        # Get VN response
        ai_chat_bot.send_message(img)
        description = ai_chat_bot.send_message("Describe this image.")

        bot.send_photo(chat_id=message.chat.id, photo=img_byte_arr)
        bot.send_message(message.chat.id, description)

@bot.message_handler(commands=['describe_scene'])
def send_camera_metadata(message):
    if camera_queue is not None:
        image_array = []
        while not camera_queue.empty():
            image_array.insert(0, camera_queue.get()['image'])
        
        video_data = video_utils.create_mp4_from_images(image_array)
        video_data.seek(0)
        
        # Debug
        #if video_data:
        #    with open('/home/pi/Desktop/my_video.mp4', 'wb') as f:
        #        f.write(video_data.getbuffer())
                
        video_data.seek(0)
        # Get VN response
        description =  ai_chat_bot.generate_content(prompt="Describe this video.", 
                                                    video_data=video_data.getvalue())

        bot.send_video(chat_id=message.chat.id, video=video_data)
        bot.send_message(message.chat.id, description)

@bot.message_handler(content_types=['text'])
def echo_all(message):
    response = ai_chat_bot.send_message(message.text)
    bot.send_message(message.chat.id, response)
    asyncio.run(say(response.replace('*','')))
    hailo_bot.do_action(response)

@bot.message_handler(content_types=['voice','audio'])
def voice_processing(message):
    # Get voice note
    file_info = bot.get_file(message.voice.file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    # Get VN response
    prompt = "Transcribe this audio."
    transcription = ai_chat_bot.generate_content(prompt=prompt, mime_type="audio/ogg", data=downloaded_file)

    # Respond
    response = ai_chat_bot.send_message(transcription)
    bot.send_message(message.chat.id, response)
    asyncio.run(say(response.replace('*','')))

if __name__ == '__main__':
    bot.infinity_polling()