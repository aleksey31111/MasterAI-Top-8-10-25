import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, JobQueue
)
from telegram.constants import ParseMode

import config
from storage import AsyncJSONStorage
from utils import (
    format_progress_bar, get_week_calendar,
    calculate_streak, get_timezone_time, format_habit_list
)


class HabitTrackerBot:
    def __init__(self):
        self.storage = AsyncJSONStorage()
        self.application = None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start."""
        user = update.effective_user
        welcome_text = (
            f"👋 Привет, {user.first_name}!\n\n"
            "Я — бот для отслеживания привычек. Помогу тебе стать лучше!\n\n"
            "📝 **Доступные команды:**\n"
            "/add_habit [название] - добавить новую привычку\n"
            "/list_habits - список всех привычек\n"
            "/check [номер] - отметить выполнение привычки сегодня\n"
            "/stats [дней] - статистика за N дней (по умолчанию 7)\n"
            "/reset - сбросить все привычки\n\n"
            "⏰ Ежедневно в 9:00 я буду присылать напоминание!"
        )

        # Создаем запись пользователя, если её нет
        user_data = await self.storage.get_user_data(user.id)
        await self.storage.save_user_data(user.id, user_data)

        await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

    async def add_habit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавление новой привычки: /add_habit Зарядка."""
        if not context.args:
            await update.message.reply_text(
                "❌ Пожалуйста, укажите название привычки.\n"
                "Пример: /add_habit Читать 20 минут"
            )
            return

        habit_name = " ".join(context.args)
        user_id = update.effective_user.id

        # Получаем данные пользователя
        user_data = await self.storage.get_user_data(user_id)
        habits = user_data.get("habits", [])

        # Создаем новую привычку
        new_habit = {
            "id": len(habits) + 1,
            "name": habit_name,
            "created": datetime.now().strftime("%Y-%m-%d"),
            "history": [],
            "streak": 0
        }

        habits.append(new_habit)
        user_data["habits"] = habits

        # Сохраняем
        await self.storage.save_user_data(user_id, user_data)

        await update.message.reply_text(
            f"✅ Привычка **{habit_name}** добавлена!\n"
            f"ID: {new_habit['id']} - используйте /check {new_habit['id']} для отметки",
            parse_mode=ParseMode.MARKDOWN
        )

    async def list_habits(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список привычек с инлайн-кнопками для быстрой отметки."""
        user_id = update.effective_user.id
        user_data = await self.storage.get_user_data(user_id)
        habits = user_data.get("habits", [])

        if not habits:
            await update.message.reply_text(
                "📭 У вас пока нет привычек. Добавьте первую с помощью /add_habit"
            )
            return

        # Форматируем текст
        message = format_habit_list(habits)

        # Создаем инлайн-клавиатуру для быстрой отметки
        # Показываем только непривычки, не отмеченные сегодня
        today_str = datetime.now().strftime("%Y-%m-%d")
        unchecked_habits = [
            h for h in habits
            if today_str not in h.get("history", [])
        ]

        keyboard = []
        if unchecked_habits:
            # Создаем кнопки для первых 3 непривычек
            row = []
            for habit in unchecked_habits[:3]:
                row.append(
                    InlineKeyboardButton(
                        f"✅ {habit['name'][:10]}...",
                        callback_data=f"check_{habit['id']}"
                    )
                )
            keyboard.append(row)

            # Кнопка "Отметить все"
            if len(unchecked_habits) > 1:
                keyboard.append([
                    InlineKeyboardButton(
                        "✅ Отметить все сегодня",
                        callback_data="check_all"
                    )
                ])

        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

        await update.message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

    async def check_habit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отметить выполнение привычки: /check 1."""
        if not context.args:
            await update.message.reply_text(
                "❌ Пожалуйста, укажите номер привычки.\n"
                "Пример: /check 1\n"
                "Используйте /list_habits чтобы увидеть номера"
            )
            return

        try:
            habit_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Номер привычки должен быть числом!")
            return

        user_id = update.effective_user.id
        user_data = await self.storage.get_user_data(user_id)
        habits = user_data.get("habits", [])

        # Ищем привычку
        habit_found = None
        for habit in habits:
            if habit["id"] == habit_id:
                habit_found = habit
                break

        if not habit_found:
            await update.message.reply_text("❌ Привычка с таким ID не найдена!")
            return

        # Отмечаем выполнение
        today_str = datetime.now().strftime("%Y-%m-%d")
        history = habit_found.get("history", [])

        if today_str in history:
            await update.message.reply_text(
                f"ℹ️ Привычка **{habit_found['name']}** уже отмечена сегодня!",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        history.append(today_str)
        habit_found["history"] = history
        habit_found["streak"] = calculate_streak(history)

        # Сохраняем изменения
        await self.storage.save_user_data(user_id, user_data)

        # Формируем ответ
        total_days = len(history)
        streak = habit_found["streak"]
        week_history = [d for d in history
                        if (datetime.now().date() - datetime.strptime(d, "%Y-%m-%d").date()).days < 7]

        response = (
            f"🎉 **Отлично!** Привычка **{habit_found['name']}** выполнена!\n\n"
            f"📊 **Прогресс:**\n"
            f"• 🔥 Текущая серия: {streak} дн.\n"
            f"• 📅 Всего выполнено: {total_days} дн.\n"
            f"• 📈 За неделю: {len(week_history)}/7 дн.\n"
            f"• {format_progress_bar(len(week_history), 7, 5)}\n\n"
            f"{get_week_calendar(history)}"
        )

        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать статистику: /stats 7."""
        try:
            days = int(context.args[0]) if context.args else 7
        except ValueError:
            days = 7

        user_id = update.effective_user.id
        user_data = await self.storage.get_user_data(user_id)
        habits = user_data.get("habits", [])

        if not habits:
            await update.message.reply_text("📭 У вас пока нет привычек для статистики.")
            return

        # Рассчитываем статистику
        today = datetime.now().date()
        period_start = today - timedelta(days=days - 1)

        total_completions = 0
        habit_stats = []

        for habit in habits:
            history = habit.get("history", [])
            period_completions = sum(
                1 for date_str in history
                if period_start <= datetime.strptime(date_str, "%Y-%m-%d").date() <= today
            )

            total_completions += period_completions

            habit_stats.append({
                "name": habit["name"],
                "completions": period_completions,
                "percentage": (period_completions / days) * 100 if days > 0 else 0
            })

        # Сортируем по проценту выполнения
        habit_stats.sort(key=lambda x: x["percentage"], reverse=True)

        # Формируем отчет
        response = [
            f"📈 **Статистика за последние {days} дней**\n",
            f"📊 **Общая эффективность:** {format_progress_bar(total_completions, days * len(habits), 10)}\n"
        ]

        for stat in habit_stats:
            bar = format_progress_bar(stat["completions"], days, 5)
            response.append(
                f"• **{stat['name']}**: {stat['completions']}/{days} дн. | {bar}"
            )

        # Лучшая и худшая привычка
        if habit_stats:
            best = habit_stats[0]
            worst = habit_stats[-1] if len(habit_stats) > 1 else None

            response.append(f"\n🏆 **Лучшая привычка**: {best['name']} ({best['completions']}/{days} дн.)")
            if worst and worst != best:
                response.append(f"📉 **Нужно улучшить**: {worst['name']} ({worst['completions']}/{days} дн.)")

        await update.message.reply_text("\n".join(response), parse_mode=ParseMode.MARKDOWN)

    async def reset_habits(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбросить все привычки (требует подтверждения)."""
        keyboard = [
            [
                InlineKeyboardButton("❌ Отмена", callback_data="cancel_reset"),
                InlineKeyboardButton("✅ Да, сбросить", callback_data="confirm_reset")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "⚠️ **Внимание!** Вы уверены, что хотите сбросить ВСЕ привычки?\n"
            "Это действие невозможно отменить!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на инлайн-кнопки."""
        query = update.callback_query
        await query.answer()  # Подтверждаем нажатие

        user_id = query.from_user.id
        data = query.data

        if data.startswith("check_"):
            # Обработка отметки привычки через кнопку
            if data == "check_all":
                # Отметить все непривычки сегодня
                user_data = await self.storage.get_user_data(user_id)
                habits = user_data.get("habits", [])
                today_str = datetime.now().strftime("%Y-%m-%d")
                updated_count = 0

                for habit in habits:
                    if today_str not in habit.get("history", []):
                        habit["history"].append(today_str)
                        habit["streak"] = calculate_streak(habit["history"])
                        updated_count += 1

                if updated_count > 0:
                    await self.storage.save_user_data(user_id, user_data)
                    await query.edit_message_text(
                        f"✅ Отмечено {updated_count} привычек за сегодня!\n"
                        f"Используйте /stats для просмотра прогресса.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await query.edit_message_text(
                        "ℹ️ Все привычки уже отмечены сегодня!",
                        parse_mode=ParseMode.MARKDOWN
                    )
            else:
                # Отметить конкретную привычку
                habit_id = int(data.split("_")[1])
                user_data = await self.storage.get_user_data(user_id)
                habits = user_data.get("habits", [])

                for habit in habits:
                    if habit["id"] == habit_id:
                        today_str = datetime.now().strftime("%Y-%m-%d")
                        if today_str not in habit.get("history", []):
                            habit["history"].append(today_str)
                            habit["streak"] = calculate_streak(habit["history"])
                            await self.storage.save_user_data(user_id, user_data)

                            await query.edit_message_text(
                                f"✅ Привычка **{habit['name']}** отмечена!\n"
                                f"Текущая серия: {habit['streak']} дн.",
                                parse_mode=ParseMode.MARKDOWN
                            )
                        else:
                            await query.edit_message_text(
                                f"ℹ️ Привычка **{habit['name']}** уже отмечена сегодня!",
                                parse_mode=ParseMode.MARKDOWN
                            )
                        break

        elif data == "confirm_reset":
            # Подтверждение сброса
            await self.storage.delete_user_data(user_id)
            await query.edit_message_text(
                "🗑️ Все привычки сброшены!\n"
                "Начните с чистого листа с помощью /add_habit"
            )

        elif data == "cancel_reset":
            # Отмена сброса
            await query.edit_message_text("✅ Сброс отменен.")

    async def daily_reminder(self, context: ContextTypes.DEFAULT_TYPE):
        """Ежедневное напоминание в 9:00."""
        job = context.job
        user_id = job.user_id

        # Получаем данные пользователя
        user_data = await self.storage.get_user_data(user_id)
        habits = user_data.get("habits", [])

        if not habits:
            return  # У пользователя нет привычек

        # Проверяем, какие привычки не выполнены сегодня
        today_str = datetime.now().strftime("%Y-%m-%d")
        unchecked_habits = [
            habit for habit in habits
            if today_str not in habit.get("history", [])
        ]

        if not unchecked_habits:
            message = "🎉 **Все привычки выполнены сегодня!** Отличная работа! 🏆"
        else:
            habit_list = "\n".join([f"• {h['name']}" for h in unchecked_habits[:5]])
            if len(unchecked_habits) > 5:
                habit_list += f"\n• ... и ещё {len(unchecked_habits) - 5}"

            message = (
                "⏰ **Доброе утро!** Время проверить привычки!\n\n"
                f"📝 **Не выполнено сегодня:**\n{habit_list}\n\n"
                f"Используйте /list_habits для быстрой отметки!"
            )

        # Отправляем напоминание
        await context.bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode=ParseMode.MARKDOWN
        )

    async def setup_jobs(self, application: Application):
        """Настройка ежедневных напоминаний для всех пользователей."""
        # Эта функция вызывается при запуске бота
        # В реальном проекте нужно получать список пользователей из БД
        # Для примера - просто добавляем задачу, которая будет проверяться

        # Альтернативный подход: добавляем задачи при первом взаимодействии
        # Для этого можно использовать ConversationHandler или сохранять задачи в БД
        pass

    def run(self):
        """Запуск бота."""
        # Создаем Application[citation:9]
        self.application = Application.builder().token(config.BOT_TOKEN).build()

        # Добавляем обработчики команд
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("add_habit", self.add_habit))
        self.application.add_handler(CommandHandler("list_habits", self.list_habits))
        self.application.add_handler(CommandHandler("check", self.check_habit))
        self.application.add_handler(CommandHandler("stats", self.show_stats))
        self.application.add_handler(CommandHandler("reset", self.reset_habits))

        # Добавляем обработчик инлайн-кнопок
        self.application.add_handler(CallbackQueryHandler(self.button_callback))

        # Запускаем бота
        print("🤖 Бот запущен...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


async def main():
    """Точка входа для асинхронного запуска."""
    bot = HabitTrackerBot()

    # Запускаем бота
    await bot.application.run_polling()


if __name__ == "__main__":
    # Для простоты используем синхронный запуск
    bot = HabitTrackerBot()
    bot.run()