from datetime import date, timedelta

def progress_bar(completed_days: int, total_days: int) -> str:
    percent_complete = completed_days * 100 // total_days
    bar_length = 10
    filled_length = min(bar_length, max(percent_complete // 10, 0))
    empty_length = bar_length - filled_length
    return f"{'█' * filled_length}{'░' * empty_length}"

def format_date(date_obj: date) -> str:
    return date_obj.strftime("%Y-%m-%d")

def days_ago(n: int) -> date:
    return date.today() - timedelta(days=n)

def is_today_in_history(history_list: List[str]) -> bool:
    today_str = format_date(date.today())
    return today_str in history_list