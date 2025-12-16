import os
import telebot
from Basket.workflow import WorkflowManager
from project_db import ProjectDatabase
from dotenv import load_dotenv

load_dotenv()

# TOKEN = "ВАШ_ТОКЕН"
bot = telebot.TeleBot(os.getenv("TOKEN"))
db = ProjectDatabase()
workflow_manager = WorkflowManager(bot, db)

@bot.message_handler(commands=["start"])
def welcome(message):
    bot.reply_to(message, "Добро пожаловать в Content Generator Bot!\nНачните с команды /help.")

@bot.message_handler(commands=["help"])
def help_commands(message):
    commands = """
    Доступные команды:
    /write - Генерация текста
    /idea - Генерация идей
    /improve - Улучшение существующего текста
    /translate - Перевод текста
    /style - Изменение стиля текста
    """
    bot.reply_to(message, commands)

@bot.message_handler(commands=["write"])
def write_command(message):
    workflow_manager.start_workflow(message, "generate_text")

@bot.message_handler(commands=["idea"])
def idea_command(message):
    workflow_manager.start_workflow(message, "generate_ideas")

@bot.message_handler(content_types=["text"])
def handle_messages(message):
    workflow_manager.handle_step(message)

bot.polling()