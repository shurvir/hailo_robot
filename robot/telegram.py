import os
import telebot
import google.generativeai as genai
from google.cloud import speech
from markdownify import markdownify as md
import os
from tts import say
import asyncio
import pathlib

BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")
chat = model.start_chat()
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(content_types=['text'])
def echo_all(message):
    response = chat.send_message(message.text).text
    bot.send_message(message.chat.id, response)
    asyncio.run(say(response.replace('*','')))

@bot.message_handler(content_types=['voice','audio'])
def voice_processing(message):
    # Get voice note
    file_info = bot.get_file(message.voice.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    with open('/home/pi/Documents/hailo_robot/test_data/audio/new_file.ogg', 'wb') as new_file:
        new_file.write(downloaded_file)

    # Get VN response
    prompt = "Transcribe this audio."
    transcription = model.generate_content([
        prompt,
        {
            "mime_type": "audio/ogg",
            "data": pathlib.Path('/home/pi/Documents/hailo_robot/test_data/audio/new_file.ogg').read_bytes()
        }
    ]).text

    # respond
    response = chat.send_message(transcription).text
    bot.send_message(message.chat.id, response)
    asyncio.run(say(response.replace('*','')))

bot.infinity_polling()