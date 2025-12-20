from datetime import datetime, timedelta
from typing import List, Dict, Any
import pytz


def format_progress_bar(done: int, total: int, width: int = 5) -> str:
    """
    Создает текстовый прогресс-бар.
    Пример: ▰▰▰▱▱ 60%
    """
    if total == 0:
        return "▱" * width + " 0%"

    percentage = min(100, int((done / total) * 100))
    filled = int(width * done / total)
    bar = "▰" * filled + "▱" * (width - filled)
    return f"{bar} {percentage}%"


def get_week_calendar(history: List[str], days: int = 7) -> str:
    """
    Создает календарь выполнения за неделю.
    Пример: Пн:✅ Вт:❌ Ср:🔘 Чт:✅ Пт:🔘 Сб:🔘 Вс:🔘
    """
    today = datetime.now().date()
    weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    result = []

    for i in range(days):
        date = today - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")

        if date_str in history:
            emoji = "✅"
        elif date.weekday() >= 5:  # Суббота и воскресенье
            emoji = "🔘"
        else:
            emoji = "❌"

        result.append(f"{weekdays[date.weekday()]}:{emoji}")

    return " ".join(reversed(result))


def calculate_streak(history: List[str]) -> int:
    """Рассчитывает текущую серию выполненных дней подряд."""
    if not history:
        return 0

    today = datetime.now().date()
    dates = sorted([datetime.strptime(d, "%Y-%m-%d").date() for d in history])

    streak = 0
    current_date = today

    # Проверяем последовательные дни с сегодняшнего назад
    while current_date in dates:
        streak += 1
        current_date -= timedelta(days=1)

    return streak


def get_timezone_time(user_timezone: str = "Europe/Moscow") -> datetime:
    """Получение текущего времени в часовом поясе пользователя."""
    try:
        tz = pytz.timezone(user_timezone)
        return datetime.now(tz)
    except pytz.exceptions.UnknownTimeZoneError:
        # Возвращаем время по умолчанию (Москва)
        return datetime.now(pytz.timezone("Europe/Moscow"))


def format_habit_list(habits: List[Dict[str, Any]]) -> str:
    """Форматирует список привычек для красивого отображения."""
    if not habits:
        return "📭 У вас пока нет привычек. Добавьте первую с помощью /add_habit"

    lines = ["📋 **Ваши привычки:**", ""]

    for i, habit in enumerate(habits, 1):
        streak = habit.get("streak", 0)
        total_days = len(habit.get("history", []))

        # Прогресс за последние 7 дней
        week_history = [d for d in habit.get("history", [])
                        if (datetime.now().date() - datetime.strptime(d, "%Y-%m-%d").date()).days < 7]
        week_progress = len(week_history)

        lines.append(
            f"{i}. **{habit['name']}**\n"
            f"   🔥 Серия: {streak} дн. | 📅 Всего: {total_days} дн.\n"
            f"   📊 Неделя: {week_progress}/7 | {format_progress_bar(week_progress, 7, 5)}\n"
            f"   {get_week_calendar(habit.get('history', []))}"
        )

    return "\n".join(lines)