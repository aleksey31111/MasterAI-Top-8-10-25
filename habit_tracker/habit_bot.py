import logging
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    filters,
    MessageHandler,
    PicklePersistence,
    ConversationHandler,
    CallbackContext,
)
from storage import Storage
from utils import format_progress_bar, format_stats, get_today_str

load_dotenv(dotenv_path=Path('.env'))

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv('BOT_TOKEN')
STORAGE_PATH = 'habits.json'

storage = Storage(STORAGE_PATH)

# Главная функция старта бота
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Привет! Я твой трекер привычек.\nИспользуй /help для ознакомления с командами.")

# Добавление новой привычки
def add_habit(update: Update, context: CallbackContext) -> None:
    habit_name = ' '.join(context.args)
    if habit_name:
        storage.add_habit(update.effective_user.id, habit_name)
        update.message.reply_text(f'Привычка "{habit_name}" добавлена.')
    else:
        update.message.reply_text("Укажите название привычки.")

# Вывод списка привычек
def list_habits(update: Update, context: CallbackContext) -> None:
    habits = storage.get_habits(update.effective_user.id)
    if habits:
        keyboard_buttons = [[InlineKeyboardButton(f"{habit['name']}", callback_data=f"habit_{habit['id']}")] for habit in habits]
        reply_markup = InlineKeyboardMarkup(keyboard_buttons)
        update.message.reply_text("Твои привычки:", reply_markup=reply_markup)
    else:
        update.message.reply_text("Нет зарегистрированных привычек.")

# Отметка выполнения привычки
def check_habit(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    habit_id = int(query.data.split('_')[1])
    habits = storage.get_habits(update.effective_user.id)
    habit = next((h for h in habits if h['id'] == habit_id), None)
    if habit:
        today = get_today_str()
        if today not in habit["history"]:
            habit["history"].append(today)
            habit["streak"] += 1
            storage.update_habit(update.effective_user.id, habit)
            query.answer(f'Привычка "{habit["name"]}" отмечена как выполненная!')
        else:
            query.answer('Сегодняшний день уже отмечен.', show_alert=True)
    else:
        query.answer('Привычка не найдена.', show_alert=True)

# Показ статистики
def stats(update: Update, context: CallbackContext) -> None:
    if context.args:
        days = int(context.args[0])
        habits = storage.get_habits(update.effective_user.id)
        results = ""
        for habit in habits:
            results += format_stats(habit, days) + "\n"
        update.message.reply_text(results)
    else:
        update.message.reply_text("Укажите количество дней.")

# Сброс всех привычек
def reset(update: Update, context: CallbackContext) -> None:
    storage.reset_habits(update.effective_user.id)
    update.message.reply_text("Все привычки удалены.")

# Неизвестная команда
def unknown_command(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Неизвестная команда. Воспользуйся /help.")

# Справочная информация
def help(update: Update, context: CallbackContext) -> None:
    commands = """
/add_habit <Название> - Добавить привычку
/list_habits - Посмотреть список привычек
/check <Номер> - Отметить выполнение привычки
/stats <Кол-во дней> - Показать статистику
/reset - Удалить все привычки
"""
    update.message.reply_text(commands)

# Настройка расписания ежедневных напоминаний
def setup_jobs(dispatcher):
    job_queue = dispatcher.job_queue
    job_queue.run_daily(send_reminders, time=datetime.time(hour=9))  # 9:00 утра

# Функция ежедневных напоминаний
def send_reminders(context: CallbackContext):
    users = storage.get_all_users()
    for user_id in users:
        habits = storage.get_habits(user_id)
        message = "Доброе утро! Сегодняшние привычки:\n"
        for habit in habits:
            message += f"- {habit['name']}\n"
        context.bot.send_message(chat_id=user_id, text=message)

# Главный запуск бота
def main():
    persistence = PicklePersistence(filename='habit_bot_persistence.pickle')
    updater = Updater(TOKEN, persistence=persistence, use_context=True)
    dp = updater.dispatcher

    # Обработчики команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("add_habit", add_habit))
    dp.add_handler(CommandHandler("list_habits", list_habits))
    dp.add_handler(CallbackQueryHandler(check_habit))
    dp.add_handler(CommandHandler("stats", stats))
    dp.add_handler(CommandHandler("reset", reset))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(MessageHandler(filters.command, unknown_command))

    # Настройка расписания
    setup_jobs(dp)

    # Запуск бота
    updater.start_polling()
    logger.info("Habit tracker bot started...")
    updater.idle()

if __name__ == '__main__':
    main()