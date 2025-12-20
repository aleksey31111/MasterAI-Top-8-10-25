import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from storage import HabitStorage
from utils import progress_bar, weekly_calendar
import datetime
import pytz


class HabitBot:
    def __init__(self, token):
        self.app = Application.builder().token(token).build()
        self.storage = HabitStorage('habits.json')
        self._register_handlers()
        self.reminder_jobs = {}

    def _register_handlers(self):
        self.app.add_handler(CommandHandler('add_habit', self.add_habit))
        self.app.add_handler(CommandHandler('list_habits', self.list_habits))
        self.app.add_handler(CommandHandler('check', self.check_habit))
        self.app.add_handler(CommandHandler('stats', self.show_stats))
        self.app.add_handler(CommandHandler('reset', self.reset_habits))
        self.app.add_handler(CommandHandler('start', self.start))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        await self.storage.init_user(user_id)
        await update.message.reply_text(
            "Привет! Я помогу тебе отслеживать привычки."
            "Доступные команды:"
            "/add_habit [название] - добавить привычку"
            "/list_habits - список привычек"
            "/check [номер] - отметить выполнение"
            "/stats [дней] - статистика"
            "/reset - сбросить все"
        )
        await self._schedule_reminder(user_id)

    async def add_habit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        habit_name = ' '.join(context.args)

        if not habit_name:
            await update.message.reply_text("Укажите название привычки: /add_habit Зарядка")
            return

        habit_id = await self.storage.add_habit(user_id, habit_name)
        await update.message.reply_text(f"✅ Привычка '{habit_name}' добавлена (ID: {habit_id})")

    async def list_habits(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        habits = await self.storage.get_habits(user_id)

        if not habits:
            await update.message.reply_text("У вас пока нет привычек. Добавьте их с помощью /add_habit")
            return

        today = datetime.date.today().isoformat()
        response = ["📝 Ваши привычки:"]

        for habit in habits:
            status = "✅" if today in habit['history'] else "❌"
            streak = f"🔥 {habit['streak']}" if habit['streak'] > 0 else ""
            response.append(
                f"{habit['id']}. {status} {habit['name']} {streak}"
                f"   📅 {len(habit['history'])} дней | {progress_bar(len(habit['history']), 30)}"
            )

        keyboard = [
            [InlineKeyboardButton(f"✅ {habit['id']}", callback_data=f"check_{habit['id']}")
             for habit in habits[:3]],
            [InlineKeyboardButton(f"✅ {habit['id']}", callback_data=f"check_{habit['id']}")
             for habit in habits[3:6]]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text("".join(response), reply_markup=reply_markup)

        async def check_habit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

            user_id = update.effective_user.id
        try:
            habit_id = int(context.args[0])
        except (IndexError, ValueError):
            await update.message.reply_text("Укажите ID привычки: /check 1")
            return

        success = await self.storage.check_habit(user_id, habit_id)
        if success:
            habit = await self.storage.get_habit(user_id, habit_id)
            await update.message.reply_text(
                f"✅ Привычка '{habit['name']}' отмечена!"
                f"Серия: {habit['streak']} дней"
                f"Всего: {len(habit['history'])} дней"
            )
        else:
            await update.message.reply_text("Привычка с таким ID не найдена")

    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        try:
            days = int(context.args[0]) if context.args else 7
        except ValueError:
            days = 7

        habits = await self.storage.get_habits(user_id)
        if not habits:
            await update.message.reply_text("У вас пока нет привычек")
            return

        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=days - 1)

        response = [f"📊 Статистика за последние {days} дней:"]
        calendar = weekly_calendar(habits, start_date, end_date)

        for habit in habits:
            completed = sum(1 for d in habit['history']
                            if start_date <= datetime.date.fromisoformat(d) <= end_date)
            percentage = int(completed / days * 100)

            response.append(
                f"{habit['id']}. {habit['name']}"
                f"   {progress_bar(percentage, 20)} {percentage}%"
                f"   🔥 Серия: {habit['streak']} дней"
            )

        await update.message.reply_text("".join(response))
        await update.message.reply_text(calendar)

        async def reset_habits(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            await self.storage.reset_user(user_id)
            await update.message.reply_text("Все привычки сброшены")

        async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            query = update.callback_query
            await query.answer()

            if query.data.startswith('check_'):
                habit_id = int(query.data.split('_')[1])
                user_id = query.from_user.id
                success = await self.storage.check_habit(user_id, habit_id)

                if success:
                    habit = await self.storage.get_habit(user_id, habit_id)
                    await query.edit_message_text(
                        f"✅ Привычка '{habit['name']}' отмечена!"
                        f"Серия: {habit['streak']} дней"
                        f"Всего: {len(habit['history'])} дней"
                    )
                else:
                    await query.edit_message_text("Ошибка: привычка не найдена")

        async def _schedule_reminder(self, user_id):
            if user_id in self.reminder_jobs:
                self.reminder_jobs[user_id].schedule_removal()

            user_data = await self.storage.get_user_data(user_id)
            timezone = pytz.timezone(user_data.get('timezone', 'Europe/Moscow'))

            def callback(context: ContextTypes.DEFAULT_TYPE):
                asyncio.create_task(self._send_reminder(user_id))

            job = self.app.job_queue.run_daily(
                callback,
                time=datetime.time(9, 0, tzinfo=timezone),
                chat_id=user_id
            )
            self.reminder_jobs[user_id] = job

        async def _send_reminder(self, user_id):
            habits = await self.storage.get_habits(user_id)
            if not habits:
                return

            today = datetime.date.today().isoformat()
            unchecked = [h for h in habits if today not in h['history']]

            if unchecked:
                message = "⏰ Напоминание! Сегодня еще не выполнено:"
    message += "".join(f"{h['id']}.{h['name']}" for h in unchecked)

keyboard = [
    [InlineKeyboardButton(f"✅ {h['id']}", callback_data=f"check_{h['id']}")
     for h in unchecked[:3]]
]
reply_markup = InlineKeyboardMarkup(keyboard)

await self.app.bot.send_message(
    chat_id=user_id,
    text=message,
    reply_markup=reply_markup
)


def run(self):
    self.app.run_polling()
