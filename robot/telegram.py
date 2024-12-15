import os
import telebot
import os
from robot import Robot
import controller
import asyncio

BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN')
ROBOT_COMMANDS = Robot.get_actions()
telegram_bot = telebot.TeleBot(BOT_TOKEN)

@telegram_bot.message_handler(commands=['pick_up'])
def go_to(message):
    controller.pick_up_object(message.text.replace('/pick_up','').strip())

@telegram_bot.message_handler(commands=['drop_off'])
def go_to(message):
    controller.drop_off_object(message.text.replace('/drop_off','').strip())

@telegram_bot.message_handler(commands=['find'])
def go_to(message):
    controller.find_object(message.text.replace('/find','').strip())

@telegram_bot.message_handler(commands=ROBOT_COMMANDS)
def do_robot_action(message):
    controller.send_action_to_robot(message.text.replace('/',''))

@telegram_bot.message_handler(commands=['get_camera_metadata'])
def send_camera_metadata(message):
    controller.get_camera_metadata(telegram_bot, message.chat.id)
        
@telegram_bot.message_handler(commands=['describe_scene'])
def describe_scene(message):
    controller.describe_scene(telegram_bot, message.chat.id)

@telegram_bot.message_handler(commands=['track_object'])
def track_object(message):
    if len(message.text.split(' ')) < 3:
        return
    object_name = ' '.join(message.text.replace('/track_object','').strip().split(' ')[0:-1])
    object_id = (int) (message.text.replace('/track_object','').strip().split(' ')[-1])
    controller.track(object_name, object_id)

@telegram_bot.message_handler(content_types=['text'])
def echo_all(message):
    controller.send_message_to_AI(message.text, telegram_bot, message.chat.id)

@telegram_bot.message_handler(content_types=['voice','audio'])
def voice_processing(message):
    # Get voice note from telegram
    file_info = telegram_bot.get_file(message.voice.file_id)
    downloaded_file = telegram_bot.download_file(file_info.file_path)

    # Send voice note to gemini for processing
    controller.process_audio(downloaded_file, telegram_bot, message.chat.id)

if __name__ == '__main__':
    telegram_bot.infinity_polling()