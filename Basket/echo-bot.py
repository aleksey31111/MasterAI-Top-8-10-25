"""
Echo Bot

Этот бот демонстрирует базовую функциональность Telegram бота:
1. Приветствие при команде "/start";
2. Эхо-повтор сообщений пользователя;
3. Ответ на команду "/help" с описанием функций бота.

Требования:
- Python >= 3.12
- Библиотека `python-telegram-bot` версии >= 20.0

Запуск:
1. Установите виртуальное окружение и зависимости командой:
   ```
   pip install python-telegram-bot[sockets]
   ```

2. Создайте файл `.env` рядом с вашим скриптом и добавьте туда токен вашего бота следующим образом:
   ```
   BOT_TOKEN=your_telegram_bot_token_here
   ```

3. Запустите скрипт командой:
   ```
   python echo_bot.py
   ```

После запуска бот начнёт отвечать на команды `/start`, `/help` и повторять любые отправленные ему сообщения.
"""

import os
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

# Загружаем токен бота из переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')


# Функция обработчик для команды '/start'
async def start(update, context):
    await update.message.reply_text("Привет! Я EchoBot. Отправьте мне сообщение, и я повторю его.")


# Функция обработчик для любого текста от пользователя
async def echo(update, context):
    # Просто возвращаем обратно полученный текст
    await update.message.reply_text(update.message.text)


# Обработчик команды '/help', вывод списка команд
async def help_command(update, context):
    text = (
        "Вот список моих команд:\n"
        "/start - Начало работы\n"
        "/help - Список команд\n"
        "Любое другое сообщение - я повторяю его."
    )
    await update.message.reply_text(text)
