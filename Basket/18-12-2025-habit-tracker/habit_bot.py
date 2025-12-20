import asyncio
import os
from distutils.cmd import Command

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters.command import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
# from aiogram.utils.callback_data import CallbackData
from aiofile import AIOFile
from asyncio import sleep
from datetime import datetime, time
from pytz import timezone
from storage import HabitStorage
from utils import *

load_dotenv()

# Настройки
TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

bot = Bot(token=TOKEN)
dp = Dispatcher()
habit_storage = HabitStorage()

# Эмоцонные обозначения статуса
STATUS_EMOJI = {'completed': '✅', 'missed': '❌'}

async def send_reminder(bot: Bot, chat_id: int, message_text: str):
    await bot.send_message(chat_id, message_text)

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await habit_storage.add_user(str(message.from_user.id), message.from_user.timezone)
    await message.answer("Привет! Я бот для отслеживания твоих привычек.")

@dp.message(Command('add_habit'))
async def add_habit_handler(message: types.Message, command: CommandObject):
    habit_name = command.args.strip()
    if habit_name:
        user_id = str(message.from_user.id)
        user_data = await habit_storage.get_user_data(user_id)
        new_habit = {
            "id": len(user_data['habits']) + 1,
            "name": habit_name,
            "created": format_date(datetime.now()),
            "history": [],
            "streak": 0
        }
        user_data['habits'].append(new_habit)
        await habit_storage.set_user_data(user_id, user_data)
        await message.reply(f"Привычка '{habit_name}' успешно добавлена!")
    else:
        await message.reply("Укажите название привычки после команды.")

@dp.message(Command('list_habits'))
async def list_habits_handler(message: types.Message):
    user_id = str(message.from_user.id)
    user_data = await habit_storage.get_user_data(user_id)
    habits = user_data.get('habits', [])
    response = "Список ваших привычек:\n\n"
    for idx, habit in enumerate(habits):
        emoji = STATUS_EMOJI['completed'] if is_today_in_history(habit['history']) else STATUS_EMOJI['missed']
        response += f"{idx+1}. {emoji} {habit['name']} ({progress_bar(len(habit['history']), 7)})\n"
    await message.reply(response or "Нет сохраненных привычек.")

@dp.message(Command('check'))
async def check_habit_handler(message: types.Message, command: CommandObject):
    habit_idx = command.args.strip()
    if habit_idx.isdigit():
        user_id = str(message.from_user.id)
        user_data = await habit_storage.get_user_data(user_id)
        habits = user_data.get('habits')
        if habits and int(habit_idx)-1 < len(habits):
            habit = habits[int(habit_idx)-1]
            if not is_today_in_history(habit['history']):
                habit['history'].append(format_date(datetime.now()))
                habit['streak'] += 1
                await habit_storage.update_habit(user_id, habit['id'], habit)
                await message.reply(f"Отмечено выполнение привычки №{habit_idx}: {habit['name']}")
            else:
                await message.reply("Сегодняшнее выполнение уже отмечено.")
        else:
            await message.reply("Неверный номер привычки.")
    else:
        await message.reply("Укажите номер привычки после команды.")

@dp.message(Command('stats'))
async def stats_handler(message: types.Message, command: CommandObject):
    num_days = command.args.strip()
    if num_days.isdigit():
        user_id = str(message.from_user.id)
        user_data = await habit_storage.get_user_data(user_id)
        habits = user_data.get('habits', [])
        report = ""
        for habit in habits:
            count = sum([is_today_in_history(habit['history']) for _ in range(int(num_days))])
            streak_percent = round(count*100/int(num_days))
            report += f"{habit['name']}: {count}/{num_days}, {streak_percent}% выполнено.\n"
        await message.reply(report or "Нет сохранённых привычек.")
    else:
        await message.reply("Укажите количество дней после команды.")

@dp.message(Command('reset'))
async def reset_handler(message: types.Message):
    user_id = str(message.from_user.id)
    await habit_storage.reset_all_habits(user_id)
    await message.reply("Все ваши привычки были сброшены.")

async def schedule_daily_reminders():
    while True:
        now_utc = datetime.utcnow().replace(tzinfo=timezone('UTC')).astimezone(timezone('Europe/Moscow'))
        if now_utc.hour == 9 and now_utc.minute == 0:
            users = habit_storage.cache.keys()
            for user_id in users:
                await send_reminder(bot, user_id, "Напоминание проверить твои привычки!")
        await sleep(60)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()  # создаем новый цикл событий
    dp.run_polling(bot)
    loop.create_task(schedule_daily_reminders())