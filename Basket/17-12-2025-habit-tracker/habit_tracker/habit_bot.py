import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    PicklePersistence,
    filters,
    CallbackContext,
)
from storage import Storage
from utils import format_progress_bar, format_stats, get_today_str

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  # Замените на действительный токен бота
STORAGE_PATH = 'habits.json'

storage = Storage(STORAGE_PATH)

# Основная логика бота

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Привет! Я твоё персональное напоминание о привычках.")

async def add_habit(update: Update, context: CallbackContext):
    habit_name = ' '.join(context.args)
    if habit_name:
        await storage.add_habit(update.effective_user.id, habit_name)
        await update.message.reply_text(f'Привычка "{habit_name}" добавлена.')
    else:
        await update.message.reply_text('Укажите название привычки.')

async def list_habits(update: Update, context: CallbackContext):
    habits = await storage.get_habits(update.effective_user.id)
    if habits:
        buttons = [[InlineKeyboardButton(f'{habit["name"]}', callback_data=f'check_{habit["id"]}')] for habit in habits]
        await update.message.reply_text('Твои привычки:', reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await update.message.reply_text('Нет зарегистрированных привычек.')

async def check_habit(update: Update, context: CallbackContext):
    query = update.callback_query
    habit_id = int(query.data.split('_')[1])
    habits = await storage.get_habits(update.effective_user.id)
    habit = next((h for h in habits if h['id'] == habit_id), None)
    if habit:
        today = get_today_str()
        if today not in habit['history']:
            habit['history'].append(today)
            habit['streak'] += 1
            await storage.update_habit(update.effective_user.id, habit)
            await query.answer(f'Привычка "{habit["name"]}" отмечена как выполненная!')
        else:
            await query.answer('Сегодняшний день уже отмечен.', show_alert=True)
    else:
        await query.answer('Привычка не найдена.', show_alert=True)

async def stats(update: Update, context: CallbackContext):
    if context.args:
        days = int(context.args[0])
        habits = await storage.get_habits(update.effective_user.id)
        result = ''
        for habit in habits:
            result += format_stats(habit, days) + '\n'
        await update.message.reply_text(result)
    else:
        await update.message.reply_text('Укажите количество дней.')

async def reset(update: Update, context: CallbackContext):
    await storage.reset_habits(update.effective_user.id)
    await update.message.reply_text('Все привычки удалены.')

async def unknown_command(update: Update, context: CallbackContext):
    await update.message.reply_text('Неизвестная команда. Попробуй /help.')

async def help(update: Update, context: CallbackContext):
    commands = '''
/add_habit <Название> - Добавить привычку
/list_habits - Список привычек
/check <Номер> - Отметить выполнение привычки
/stats <Количество дней> - Показать статистику
/reset - Удалить все привычки
'''
    await update.message.reply_text(commands)

# Настройка бота

async def main():
    persistence = PicklePersistence(filepath='habit_bot_persistence.pickle')
    app = Application.builder().token(TOKEN).persistence(persistence).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add_habit", add_habit))
    app.add_handler(CommandHandler("list_habits", list_habits))
    app.add_handler(CallbackQueryHandler(check_habit))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # Еженедельные напоминания в 9:00 утра
    app.job_queue.run_daily(send_reminders, time=datetime.time(hour=9))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await app.idle()

if __name__ == '__main__':
    asyncio.run(main())