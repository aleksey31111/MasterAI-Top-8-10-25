#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ПРОГРАММА ДЛЯ УЧЕТА ЛИЧНЫХ ФИНАНСОВ
Версия: 1.0
Описание: Программа для ведения учета доходов и расходов с сохранением в JSON
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple


class FinanceManager:
    """
    Класс для управления личными финансами.
    Хранит операции в списке словарей, работает с JSON файлом.
    """
    
    def __init__(self, filename: str = "finances.json"):
        """
        Инициализация менеджера финансов.
        
        Args:
            filename (str): Имя файла для сохранения данных
        """
        self.filename = filename
        self.operations = self._load_data()
    
    def _load_data(self) -> List[Dict]:
        """
        Загрузка данных из JSON файла.
        
        Returns:
            List[Dict]: Список операций или пустой список
        """
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as file:
                    return json.load(file)
            except (json.JSONDecodeError, FileNotFoundError):
                return []
        return []
    
    def _save_data(self) -> None:
        """
        Сохранение данных в JSON файл.
        """
        with open(self.filename, 'w', encoding='utf-8') as file:
            json.dump(self.operations, file, ensure_ascii=False, indent=2)
    
    def add_operation(self) -> None:
        """
        Добавление новой операции.
        Запрашивает данные у пользователя и сохраняет их.
        """
        print("\n" + "="*60)
        print("ДОБАВЛЕНИЕ НОВОЙ ОПЕРАЦИИ")
        print("="*60)
        
        # Ввод даты
        while True:
            date_str = input("Введите дату (ДД.ММ.ГГГГ): ").strip()
            try:
                # Преобразуем дату в строку для хранения
                datetime.strptime(date_str, '%d.%m.%Y')
                break
            except ValueError:
                print("Ошибка: Неверный формат даты! Используйте ДД.ММ.ГГГГ")
        
        # Ввод категории
        while True:
            category = input("Введите категорию (доход/расход): ").strip().lower()
            if category in ['доход', 'расход']:
                break
            print("Ошибка: Категория должна быть 'доход' или 'расход'")
        
        # Ввод суммы
        while True:
            try:
                amount = float(input("Введите сумму: ").strip())
                if amount <= 0:
                    print("Ошибка: Сумма должна быть положительным числом!")
                    continue
                break
            except ValueError:
                print("Ошибка: Введите число!")
        
        # Ввод описания
        description = input("Введите описание: ").strip()
        if not description:
            description = "Без описания"
        
        # Создаем операцию
        operation = {
            'date': date_str,
            'category': category,
            'amount': amount,
            'description': description
        }
        
        # Добавляем в список
        self.operations.append(operation)
        self._save_data()
        
        print("\n✅ Операция успешно добавлена!")
        print(f"   Дата: {date_str}")
        print(f"   Категория: {category}")
        print(f"   Сумма: {amount:,.2f} ₽")
        print(f"   Описание: {description}")
    
    def calculate_balance(self) -> Dict[str, float]:
        """
        Расчет общего баланса.
        
        Returns:
            Dict: {'balance': общий баланс, 'income': доходы, 'expense': расходы}
        """
        total_income = 0.0
        total_expense = 0.0
        
        for op in self.operations:
            if op['category'] == 'доход':
                total_income += op['amount']
            else:
                total_expense += op['amount']
        
        balance = total_income - total_expense
        
        return {
            'balance': balance,
            'income': total_income,
            'expense': total_expense
        }
    
    def show_balance(self) -> None:
        """
        Отображение текущего баланса.
        """
        stats = self.calculate_balance()
        
        print("\n" + "="*60)
        print("ТЕКУЩИЙ БАЛАНС")
        print("="*60)
        print(f"\n💰 Общий баланс: {stats['balance']:,.2f} ₽")
        print(f"📈 Всего доходов: {stats['income']:,.2f} ₽")
        print(f"📉 Всего расходов: {stats['expense']:,.2f} ₽")
        
        # Анализ состояния
        if stats['balance'] > 0:
            print("\n✅ Финансовое состояние: Положительное")
        elif stats['balance'] < 0:
            print("\n⚠️  Финансовое состояние: Отрицательное (долги)")
        else:
            print("\n➖ Финансовое состояние: Нулевое")
    
    def get_statistics_by_category(self) -> Dict[str, Dict]:
        """
        Получение статистики по категориям.
        
        Returns:
            Dict: Статистика по доходам и расходам
        """
        stats = {
            'доход': {'total': 0.0, 'count': 0},
            'расход': {'total': 0.0, 'count': 0}
        }
        
        for op in self.operations:
            category = op['category']
            stats[category]['total'] += op['amount']
            stats[category]['count'] += 1
        
        return stats
    
    def show_statistics(self) -> None:
        """
        Отображение подробной статистики.
        """
        stats = self.get_statistics_by_category()
        
        print("\n" + "="*60)
        print("СТАТИСТИКА ПО КАТЕГОРИЯМ")
        print("="*60)
        
        # Доходы
        print("\n📈 ДОХОДЫ:")
        print(f"   Количество операций: {stats['доход']['count']}")
        print(f"   Общая сумма: {stats['доход']['total']:,.2f} ₽")
        if stats['доход']['count'] > 0:
            avg_income = stats['доход']['total'] / stats['доход']['count']
            print(f"   Средняя сумма: {avg_income:,.2f} ₽")
        
        # Расходы
        print("\n📉 РАСХОДЫ:")
        print(f"   Количество операций: {stats['расход']['count']}")
        print(f"   Общая сумма: {stats['расход']['total']:,.2f} ₽")
        if stats['расход']['count'] > 0:
            avg_expense = stats['расход']['total'] / stats['расход']['count']
            print(f"   Средняя сумма: {avg_expense:,.2f} ₽")
        
        # Общее соотношение
        total_income = stats['доход']['total']
        total_expense = stats['расход']['total']
        
        if total_income > 0:
            expense_ratio = (total_expense / total_income) * 100
            print(f"\n📊 Соотношение расходов к доходам: {expense_ratio:.1f}%")
    
    def search_by_period(self) -> None:
        """
        Поиск операций за определенный период.
        """
        print("\n" + "="*60)
        print("ПОИСК ОПЕРАЦИЙ ЗА ПЕРИОД")
        print("="*60)
        
        # Ввод начальной даты
        while True:
            start_date = input("Введите начальную дату (ДД.ММ.ГГГГ): ").strip()
            try:
                datetime.strptime(start_date, '%d.%m.%Y')
                break
            except ValueError:
                print("Ошибка: Неверный формат даты!")
        
        # Ввод конечной даты
        while True:
            end_date = input("Введите конечную дату (ДД.ММ.ГГГГ): ").strip()
            try:
                datetime.strptime(end_date, '%d.%m.%Y')
                break
            except ValueError:
                print("Ошибка: Неверный формат даты!")
        
        # Поиск операций
        found_operations = []
        for op in self.operations:
            if start_date <= op['date'] <= end_date:
                found_operations.append(op)
        
        # Сортировка по дате
        found_operations.sort(key=lambda x: x['date'])
        
        # Вывод результатов
        print(f"\n📋 Найдено операций: {len(found_operations)}")
        
        if found_operations:
            print("\n" + "-"*60)
            print(f"{'№':<3} {'Дата':<12} {'Категория':<10} {'Сумма':<15} {'Описание':<20}")
            print("-"*60)
            
            total_income = 0.0
            total_expense = 0.0
            
            for i, op in enumerate(found_operations, 1):
                # Форматирование суммы
                amount_str = f"{op['amount']:,.2f} ₽"
                # Обрезка длинного описания
                description = op['description'][:20] + '...' if len(op['description']) > 20 else op['description']
                
                print(f"{i:<3} {op['date']:<12} {op['category']:<10} {amount_str:<15} {description:<20}")
                
                # Подсчет итогов
                if op['category'] == 'доход':
                    total_income += op['amount']
                else:
                    total_expense += op['amount']
            
            print("-"*60)
            print(f"\n📊 ИТОГИ ЗА ПЕРИОД:")
            print(f"   Доходы:  {total_income:,.2f} ₽")
            print(f"   Расходы: {total_expense:,.2f} ₽")
            print(f"   Баланс:  {total_income - total_expense:,.2f} ₽")
    
    def show_all_operations(self) -> None:
        """
        Отображение всех операций.
        """
        if not self.operations:
            print("\n❌ Операций еще нет")
            return
        
        print("\n" + "="*60)
        print("ВСЕ ОПЕРАЦИИ")
        print("="*60)
        
        # Сортировка по дате (новые сверху)
        sorted_ops = sorted(self.operations, key=lambda x: x['date'], reverse=True)
        
        print(f"\n{'№':<3} {'Дата':<12} {'Категория':<10} {'Сумма':<15} {'Описание':<20}")
        print("-"*60)
        
        for i, op in enumerate(sorted_ops, 1):
            amount_str = f"{op['amount']:,.2f} ₽"
            description = op['description'][:20] + '...' if len(op['description']) > 20 else op['description']
            print(f"{i:<3} {op['date']:<12} {op['category']:<10} {amount_str:<15} {description:<20}")
        
        # Показываем общую статистику
        stats = self.calculate_balance()
        print("\n" + "="*60)
        print(f"💰 ОБЩИЙ БАЛАНС: {stats['balance']:,.2f} ₽")
        print(f"   Доходы: {stats['income']:,.2f} ₽")
        print(f"   Расходы: {stats['expense']:,.2f} ₽")
    
    def delete_operation(self) -> None:
        """
        Удаление операции по номеру.
        """
        if not self.operations:
            print("\n❌ Нет операций для удаления")
            return
        
        # Показываем список операций
        print("\n" + "="*60)
        print("УДАЛЕНИЕ ОПЕРАЦИИ")
        print("="*60)
        
        # Сортировка по дате (новые сверху)
        sorted_ops = sorted(self.operations, key=lambda x: x['date'], reverse=True)
        
        print(f"\n{'№':<3} {'Дата':<12} {'Категория':<10} {'Сумма':<15} {'Описание':<20}")
        print("-"*60)
        
        for i, op in enumerate(sorted_ops, 1):
            amount_str = f"{op['amount']:,.2f} ₽"
            description = op['description'][:20] + '...' if len(op['description']) > 20 else op['description']
            print(f"{i:<3} {op['date']:<12} {op['category']:<10} {amount_str:<15} {description:<20}")
        
        # Выбор операции для удаления
        try:
            choice = int(input(f"\nВведите номер операции для удаления (1-{len(sorted_ops)}): "))
            if 1 <= choice <= len(sorted_ops):
                # Находим операцию в исходном списке
                op_to_delete = sorted_ops[choice - 1]
                
                # Удаляем из исходного списка
                for i, op in enumerate(self.operations):
                    if (op['date'] == op_to_delete['date'] and 
                        op['category'] == op_to_delete['category'] and 
                        op['amount'] == op_to_delete['amount'] and 
                        op['description'] == op_to_delete['description']):
                        del self.operations[i]
                        break
                
                self._save_data()
                print("\n✅ Операция успешно удалена!")
                print(f"   Дата: {op_to_delete['date']}")
                print(f"   Категория: {op_to_delete['category']}")
                print(f"   Сумма: {op_to_delete['amount']:,.2f} ₽")
                print(f"   Описание: {op_to_delete['description']}")
            else:
                print("\n❌ Неверный номер операции!")
        except ValueError:
            print("\n❌ Введите корректное число!")
    
    def generate_sample_data(self) -> None:
        """
        Генерация тестовых данных для демонстрации.
        """
        sample_data = [
            {'date': '01.01.2024', 'category': 'доход', 'amount': 50000.00, 'description': 'Зарплата'},
            {'date': '05.01.2024', 'category': 'расход', 'amount': 15000.00, 'description': 'Аренда квартиры'},
            {'date': '10.01.2024', 'category': 'расход', 'amount': 5000.00, 'description': 'Продукты'},
            {'date': '15.01.2024', 'category': 'расход', 'amount': 2000.00, 'description': 'Транспорт'},
            {'date': '20.01.2024', 'category': 'доход', 'amount': 10000.00, 'description': 'Фриланс'},
            {'date': '25.01.2024', 'category': 'расход', 'amount': 3000.00, 'description': 'Ресторан'},
            {'date': '28.01.2024', 'category': 'расход', 'amount': 1500.00, 'description': 'Развлечения'},
        ]
        
        self.operations.extend(sample_data)
        self._save_data()
        print("\n✅ Тестовые данные успешно добавлены!")


def print_menu() -> None:
    """
    Отображение главного меню программы.
    """
    print("\n" + "="*60)
    print("💰 ПРОГРАММА УЧЕТА ЛИЧНЫХ ФИНАНСОВ")
    print("="*60)
    print("1. 📝 Добавить операцию")
    print("2. 💰 Показать баланс")
    print("3. 📊 Показать статистику")
    print("4. 🔍 Поиск операций за период")
    print("5. 📋 Показать все операции")
    print("6. 🗑️  Удалить операцию")
    print("7. 🎲 Сгенерировать тестовые данные")
    print("0. 🚪 Выход")
    print("="*60)


def main():
    """
    Главная функция программы.
    """
    # Инициализация менеджера финансов
    fm = FinanceManager()
    
    print("\nДобро пожаловать в программу учета личных финансов!")
    print(f"Загружено операций: {len(fm.operations)}")
    
    while True:
        print_menu()
        
        choice = input("\nВыберите действие (0-7): ").strip()
        
        if choice == '1':
            fm.add_operation()
        elif choice == '2':
            fm.show_balance()
        elif choice == '3':
            fm.show_statistics()
        elif choice == '4':
            fm.search_by_period()
        elif choice == '5':
            fm.show_all_operations()
        elif choice == '6':
            fm.delete_operation()
        elif choice == '7':
            fm.generate_sample_data()
        elif choice == '0':
            print("\n💾 Сохранение данных...")
            fm._save_data()
            print("👋 До свидания!")
            break
        else:
            print("\n❌ Неверный выбор! Пожалуйста, выберите пункт от 0 до 7.")
        
        input("\nНажмите Enter для продолжения...")


if __name__ == "__main__":
    main()