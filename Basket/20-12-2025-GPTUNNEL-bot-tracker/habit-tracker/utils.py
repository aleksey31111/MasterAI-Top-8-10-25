from datetime import datetime, date, timedelta


def progress_bar(percentage, width=20):
    filled = int(percentage / 100 * width)
    return f"{'▰' * filled}{'▱' * (width - filled)}"


def weekly_calendar(habits, start_date, end_date):
    days = (end_date - start_date).days + 1
    weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

    # Create header
    header = []
    current_date = start_date
    for _ in range(days):
        header.append(f"{weekdays[current_date.weekday()]} {current_date.day}")
        current_date += timedelta(days=1)

    # Create calendar rows
    rows = []
    for habit in habits:
        row = [f"{habit['id']}. {habit['name'][:10]}"]
        current_date = start_date
        for _ in range(days):
            status = "✅" if current_date.isoformat() in habit['history'] else "❌"
            row.append(status)
            current_date += timedelta(days=1)
        rows.append(" ".join(row))

    return "📅 Календарь выполнения:


" + " ".join(header) + "
" + "
".join(rows)
