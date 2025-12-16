from datetime import datetime, timedelta

def format_progress_bar(completed_days: int, total_days: int) -> str:
    filled_blocks = '█' * (completed_days // total_days * 10)
    empty_blocks = '-' * (10 - len(filled_blocks))
    return f'[{filled_blocks}{empty_blocks}] {completed_days}/{total_days}'

def format_stats(habit: Dict, days: int) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    complete_days = sum(1 for d in habit["history"][-days:] if d <= today)
    percentage = round(complete_days / days * 100)
    return f'{habit["name"]}: {complete_days}/{days} ({percentage}%) {format_progress_bar(complete_days, days)}'

def get_today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")