# core/bot_instance.py
import os
from telegram.ext import Application 

BOT_TOKEN = os.getenv("BOT_TOKEN")

application = Application.builder().token(BOT_TOKEN).build()
bot = application.bot