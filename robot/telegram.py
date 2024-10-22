import os
import telebot
import io
import gemini
import os
from tts import say
import asyncio
import robot
from PIL import Image

BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)
hailo_bot = robot.Robot(speed=10, acceleration=10)
gemini_chat = gemini.GeminiChat()
camera_queue = None

@bot.message_handler(commands=['turn_left', 'turn_right', 'go_up', 'go_down', 'light_on', 'light_off', 'look_around'])
def do_action(message):
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
        prompt = "Describe this image."
        description = gemini_chat.generate_content(prompt=prompt, mime_type="image/png", data=img_byte_arr.getvalue())

        bot.send_photo(chat_id=message.chat.id, photo=img_byte_arr)
        bot.send_message(message.chat.id, description)

@bot.message_handler(content_types=['text'])
def echo_all(message):
    response = gemini_chat.send_message(message.text).text
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
    transcription = gemini_chat.generate_content(prompt=prompt, mime_type="audio/ogg", data=downloaded_file)

    # Respond
    response = gemini_chat.send_message(transcription).text
    bot.send_message(message.chat.id, response)
    asyncio.run(say(response.replace('*','')))

def get_camera_metadata():
    if camera_queue is not None:
        camera_metadata = camera_queue.get()
        print(camera_metadata)
        return camera_metadata
    else:
        return None

if __name__ == '__main__':
    bot.infinity_polling()