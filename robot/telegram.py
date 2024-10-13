import os
import telebot
import google.generativeai as genai
from markdownify import markdownify as md
import os

BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")
chat = model.start_chat()
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    response = chat.send_message(message.text).text
    bot.send_message(message.chat.id, response)

bot.infinity_polling()