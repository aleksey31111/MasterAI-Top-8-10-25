"""
Пользовательские фильтры для шаблонов
"""
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Получение значения из словаря по ключу
    Использование: {{ dict|get_item:key }}
    """
    return dictionary.get(key)


@register.filter
def negative(value):
    """
    Преобразование числа в отрицательное
    """
    try:
        return -float(value)
    except (ValueError, TypeError):
        return 0