import os
from dotenv import load_dotenv

load_dotenv()  # Загружает переменные из .env

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Не задан BOT_TOKEN в переменных окружения .env")

# Путь к файлу данных
DATA_FILE = "habits.json"