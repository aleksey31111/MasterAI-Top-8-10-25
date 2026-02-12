"""
Представления для приложения finances
"""
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from datetime import datetime

from .utils import (
    init_operations_session,
    get_operations,
    add_operation_to_session,
    delete_operation_from_session,
    calculate_balance,
    get_statistics_by_category,
    filter_operations_by_date,
    validate_operation_data
)


def dashboard(request):
    """
    Главная страница - дашборд.
    Отображает общий баланс и последние операции.
    """
    # Инициализируем сессию
    init_operations_session(request)

    # Получаем все операции
    operations = get_operations(request)

    # Рассчитываем баланс
    balance_data = calculate_balance(operations)

    # Получаем последние 5 операций
    recent_operations = sorted(
        operations,
        key=lambda x: x['date'],
        reverse=True
    )[:5]

    context = {
        'balance': balance_data['balance'],
        'income': balance_data['income'],
        'expense': balance_data['expense'],
        'recent_operations': recent_operations,
        'total_operations': len(operations),
    }

    return render(request, 'finances/dashboard.html', context)


def add_operation(request):
    """
    Добавление новой операции.
    """
    init_operations_session(request)

    if request.method == 'POST':
        # Получаем данные из формы
        date = request.POST.get('date', '')
        category = request.POST.get('category', '')
        amount = request.POST.get('amount', '')
        description = request.POST.get('description', '')

        # Валидация
        validation = validate_operation_data(date, category, amount, description)

        if validation['is_valid']:
            # Создаем операцию
            operation = {
                'date': validation['data']['date'],
                'category': validation['data']['category'],
                'amount': validation['data']['amount'],
                'description': validation['data']['description']
            }

            # Сохраняем в сессию
            add_operation_to_session(request, operation)

            messages.success(request, 'Операция успешно добавлена!')
            return redirect('dashboard')
        else:
            # Показываем ошибки
            for error in validation['errors']:
                messages.error(request, error)

    return render(request, 'finances/add_operation.html')


def operation_list(request):
    """
    Список всех операций.
    """
    init_operations_session(request)
    operations = get_operations(request)

    # Сортировка по дате (новые сверху)
    operations = sorted(operations, key=lambda x: x['date'], reverse=True)

    context = {
        'operations': operations,
        'total_income': calculate_balance(operations)['income'],
        'total_expense': calculate_balance(operations)['expense'],
        'balance': calculate_balance(operations)['balance'],
    }

    return render(request, 'finances/operation_list.html', context)


def delete_operation(request, operation_id):
    """
    Удаление операции по ID.
    """
    if request.method == 'POST':
        success = delete_operation_from_session(request, operation_id)

        if success:
            messages.success(request, 'Операция успешно удалена!')
        else:
            messages.error(request, 'Операция не найдена!')

    return redirect('operation_list')


def statistics(request):
    """
    Статистика по категориям.
    """
    init_operations_session(request)
    operations = get_operations(request)

    # Получаем статистику
    stats = get_statistics_by_category(operations)
    balance_data = calculate_balance(operations)

    # Доходы по месяцам (для демонстрации)
    income_by_month = {}
    expense_by_month = {}

    for op in operations:
        # Извлекаем месяц из даты
        date_parts = op['date'].split('.')
        if len(date_parts) == 3:
            month_key = f"{date_parts[1]}.{date_parts[2]}"

            if op['category'] == 'доход':
                income_by_month[month_key] = income_by_month.get(month_key, 0) + float(op['amount'])
            else:
                expense_by_month[month_key] = expense_by_month.get(month_key, 0) + float(op['amount'])

    context = {
        'stats': stats,
        'balance_data': balance_data,
        'income_by_month': dict(sorted(income_by_month.items())),
        'expense_by_month': dict(sorted(expense_by_month.items())),
    }

    return render(request, 'finances/statistics.html', context)


def search_by_period(request):
    """
    Поиск операций за определенный период.
    """
    init_operations_session(request)
    operations = get_operations(request)
    filtered_operations = []

    if request.method == 'GET' and 'start_date' in request.GET:
        start_date = request.GET.get('start_date', '')
        end_date = request.GET.get('end_date', '')

        if start_date and end_date:
            filtered_operations = filter_operations_by_date(
                operations, start_date, end_date
            )

    context = {
        'operations': filtered_operations,
        'start_date': request.GET.get('start_date', ''),
        'end_date': request.GET.get('end_date', ''),
    }

    return render(request, 'finances/search.html', context)
