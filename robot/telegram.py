import os
import telebot
import os
from robot import Robot
import controller

BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN')
ROBOT_COMMANDS = Robot.ACTIONS
telegram_bot = telebot.TeleBot(BOT_TOKEN)

@telegram_bot.message_handler(commands=['pick_up'])
def go_to(message):
    controller.pick_up_object(message.text.replace('/pick_up','').strip())


@telegram_bot.message_handler(commands=['find'])
def go_to(message):
    controller.find_object(message.text.replace('/find','').strip())

@telegram_bot.message_handler(commands=ROBOT_COMMANDS)
def do_robot_action(message):
    controller.send_action_to_robot(message.text)

@telegram_bot.message_handler(commands=['get_camera_metadata'])
def send_camera_metadata(message):
    img_byte_arr, description = controller.get_camera_metadata()
    if img_byte_arr is not None:
        telegram_bot.send_photo(chat_id=message.chat.id, photo=img_byte_arr)
        telegram_bot.send_message(message.chat.id, description)

@telegram_bot.message_handler(commands=['describe_scene'])
def send_camera_metadata(message):
    video_data, description = controller.describe_scene()
    if video_data is not None:
        telegram_bot.send_video(chat_id=message.chat.id, video=video_data)
        telegram_bot.send_message(message.chat.id, description)

@telegram_bot.message_handler(content_types=['text'])
def echo_all(message):
    response = controller.send_message_to_AI(message.text)
    telegram_bot.send_message(message.chat.id, response)

@telegram_bot.message_handler(content_types=['voice','audio'])
def voice_processing(message):
    # Get voice note from telegram
    file_info = telegram_bot.get_file(message.voice.file_id)
    downloaded_file = telegram_bot.download_file(file_info.file_path)

    # Send voice note to gemini for processing
    response = controller.process_audio(downloaded_file)

    # Send response to the chat
    telegram_bot.send_message(message.chat.id, response)

if __name__ == '__main__':
    telegram_bot.infinity_polling()