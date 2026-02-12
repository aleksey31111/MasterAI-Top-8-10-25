"""
Вспомогательные функции для работы с финансовыми операциями
"""
import json
from datetime import datetime
from typing import List, Dict, Optional


def init_operations_session(request):
    """
    Инициализация сессии для хранения операций.
    Использует список словарей - как в ТЗ.
    """
    if 'operations' not in request.session:
        request.session['operations'] = []
    return request.session['operations']


def get_operations(request) -> List[Dict]:
    """
    Получение списка операций из сессии.
    """
    return request.session.get('operations', [])


def add_operation_to_session(request, operation: Dict) -> None:
    """
    Добавление операции в сессию.

    Args:
        request: HTTP запрос
        operation: Словарь с данными операции
    """
    operations = get_operations(request)

    # Добавляем ID для удобства удаления
    if operations:
        operation['id'] = max(op.get('id', 0) for op in operations) + 1
    else:
        operation['id'] = 1

    operations.append(operation)
    request.session['operations'] = operations
    request.session.modified = True


def delete_operation_from_session(request, operation_id: int) -> bool:
    """
    Удаление операции из сессии по ID.

    Returns:
        bool: True если удаление успешно
    """
    operations = get_operations(request)
    initial_length = len(operations)

    operations = [op for op in operations if op.get('id') != operation_id]
    request.session['operations'] = operations
    request.session.modified = True

    return len(operations) < initial_length


def calculate_balance(operations: List[Dict]) -> Dict[str, float]:
    """
    Подсчет общего баланса, доходов и расходов.

    Returns:
        Dict: {'balance': общий баланс, 'income': доходы, 'expense': расходы}
    """
    total_income = 0.0
    total_expense = 0.0

    for op in operations:
        if op['category'] == 'доход':
            total_income += float(op['amount'])
        else:
            total_expense += float(op['amount'])

    balance = total_income - total_expense

    return {
        'balance': balance,
        'income': total_income,
        'expense': total_expense
    }


def get_statistics_by_category(operations: List[Dict]) -> Dict[str, Dict]:
    """
    Статистика по категориям.

    Returns:
        Dict: {'доход': {...}, 'расход': {...}}
    """
    stats = {
        'доход': {'total': 0.0, 'count': 0},
        'расход': {'total': 0.0, 'count': 0}
    }

    for op in operations:
        category = op['category']
        stats[category]['total'] += float(op['amount'])
        stats[category]['count'] += 1

    # Добавляем средние значения
    for category in stats:
        if stats[category]['count'] > 0:
            stats[category]['average'] = stats[category]['total'] / stats[category]['count']
        else:
            stats[category]['average'] = 0.0

    return stats


def filter_operations_by_date(operations: List[Dict],
                              start_date: str,
                              end_date: str) -> List[Dict]:
    """
    Фильтрация операций по диапазону дат.

    Args:
        operations: Список операций
        start_date: Начальная дата в формате ДД.ММ.ГГГГ
        end_date: Конечная дата в формате ДД.ММ.ГГГГ

    Returns:
        List[Dict]: Отфильтрованный список
    """
    filtered = []

    for op in operations:
        if start_date <= op['date'] <= end_date:
            filtered.append(op)

    # Сортировка по дате (новые сверху)
    filtered.sort(key=lambda x: x['date'], reverse=True)

    return filtered


def validate_operation_data(date_str: str,
                            category: str,
                            amount_str: str,
                            description: str) -> Dict:
    """
    Валидация данных операции.

    Returns:
        Dict: {'is_valid': bool, 'errors': list, 'data': dict}
    """
    errors = []
    data = {}

    # Проверка даты
    try:
        datetime.strptime(date_str, '%d.%m.%Y')
        data['date'] = date_str
    except ValueError:
        errors.append('Неверный формат даты. Используйте ДД.ММ.ГГГГ')

    # Проверка категории
    if category.lower() in ['доход', 'расход']:
        data['category'] = category.lower()
    else:
        errors.append('Категория должна быть "доход" или "расход"')

    # Проверка суммы
    try:
        amount = float(amount_str)
        if amount <= 0:
            errors.append('Сумма должна быть положительным числом')
        else:
            data['amount'] = amount
    except ValueError:
        errors.append('Сумма должна быть числом')

    # Проверка описания
    if description.strip():
        data['description'] = description.strip()
    else:
        errors.append('Описание не может быть пустым')

    return {
        'is_valid': len(errors) == 0,
        'errors': errors,
        'data': data
    }
