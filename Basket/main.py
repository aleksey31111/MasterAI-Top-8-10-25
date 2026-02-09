import json
import os
from datetime import datetime


def todo_list_app_pro():
    """
    Профессиональное консольное приложение списка дел
    с сохранением в файл, категориями и фильтрацией
    """

    # Конфигурация
    TASKS_FILE = "tasks.json"

    # Доступные приоритеты
    priorities = ["низкий", "средний", "высокий"]

    # Доступные категории
    categories = ["работа", "дом", "личное", "учеба", "другое"]

    def load_tasks():
        """Загрузка задач из файла"""
        if os.path.exists(TASKS_FILE):
            try:
                with open(TASKS_FILE, 'r', encoding='utf-8') as f:
                    tasks = json.load(f)
                    # Проверяем структуру задач
                    valid_tasks = []
                    for task in tasks:
                        if all(key in task for key in ['описание', 'сделана', 'приоритет', 'категория']):
                            valid_tasks.append(task)
                        else:
                            # Восстанавливаем недостающие поля
                            default_task = {
                                'описание': task.get('описание', 'Без названия'),
                                'сделана': task.get('сделана', False),
                                'приоритет': task.get('приоритет', 'средний'),
                                'категория': task.get('категория', 'другое'),
                                'дата_создания': task.get('дата_создания', datetime.now().strftime("%Y-%m-%d %H:%M")),
                                'дата_выполнения': task.get('дата_выполнения', None)
                            }
                            valid_tasks.append(default_task)
                    print(f"✅ Загружено {len(valid_tasks)} задач из файла")
                    return valid_tasks
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️ Ошибка загрузки файла: {e}. Создаю новый список.")
        return []

    def save_tasks(tasks):
        """Сохранение задач в файл"""
        try:
            with open(TASKS_FILE, 'w', encoding='utf-8') as f:
                json.dump(tasks, f, ensure_ascii=False, indent=2)
            print(f"💾 Задачи сохранены в файл {TASKS_FILE}")
        except IOError as e:
            print(f"❌ Ошибка сохранения: {e}")

    def display_tasks(tasks_list, title="СПИСОК ЗАДАЧ", show_all=True):
        """Отображение списка задач"""
        print(f"\n{'=' * 60}")
        print(f"{title}:")
        print('=' * 60)

        if not tasks_list:
            print("📭 Нет задач для отображения")
            return

        for i, task in enumerate(tasks_list, 1):
            # Статус
            status = "✅" if task['сделана'] else "⭕"

            # Приоритет с иконками
            priority_map = {
                "высокий": "🔥 ВЫСОКИЙ",
                "средний": "⚡ СРЕДНИЙ",
                "низкий": "🌿 НИЗКИЙ"
            }
            priority_display = priority_map.get(task['приоритет'], task['приоритет'])

            # Категория с иконкой
            category_map = {
                "работа": "💼 РАБОТА",
                "дом": "🏠 ДОМ",
                "личное": "👤 ЛИЧНОЕ",
                "учеба": "📚 УЧЕБА",
                "другое": "📌 ДРУГОЕ"
            }
            category_display = category_map.get(task['категория'], task['категория'])

            # Дата выполнения
            date_info = ""
            if task['сделана'] and task.get('дата_выполнения'):
                date_info = f" | Выполнено: {task['дата_выполнения']}"
            elif task.get('дата_создания'):
                date_info = f" | Создано: {task['дата_создания']}"

            print(f"{i}. {status} {task['описание']}")
            print(f"   📍 Категория: {category_display} | Приоритет: {priority_display}{date_info}")
            if i < len(tasks_list):
                print(f"   {'─' * 50}")

        # Статистика
        if show_all:
            completed = sum(1 for task in tasks_list if task['сделана'])
            print(f"\n📊 Статистика: {completed}/{len(tasks_list)} выполнено "
                  f"({completed / len(tasks_list) * 100:.0f}%)")

    def filter_tasks(tasks, filter_type):
        """Фильтрация задач"""
        if filter_type == "сделано":
            return [task for task in tasks if task['сделана']]
        elif filter_type == "не_сделано":
            return [task for task in tasks if not task['сделана']]
        elif filter_type in categories:
            return [task for task in tasks if task['категория'] == filter_type]
        return tasks

    # Загрузка задач при запуске
    tasks = load_tasks()

    print("=" * 60)
    print("        СПИСОК ДЕЛ (ПРОФЕССИОНАЛЬНАЯ ВЕРСИЯ)")
    print("=" * 60)
    print("💾 Автосохранение включено | 📁 Категории | 🔍 Фильтры")

    # Главный цикл программы
    while True:
        # Меню
        print("\n" + "═" * 50)
        print("📋 ОСНОВНОЕ МЕНЮ:")
        print("═" * 50)
        print("1. Показать все задачи")
        print("2. Добавить задачу")
        print("3. Удалить задачу")
        print("4. Отметить задачу как выполненную")
        print("5. Фильтры и категории")
        print("6. Выйти и сохранить")
        print("═" * 50)

        choice = input("Выберите действие (1-6): ").strip()

        # 1. Показать все задачи
        if choice == "1":
            display_tasks(tasks)

        # 2. Добавить задачу
        elif choice == "2":
            print("\n" + "─" * 40)
            print("➕ ДОБАВЛЕНИЕ НОВОЙ ЗАДАЧИ")
            print("─" * 40)

            # Описание
            description = input("Введите описание задачи: ").strip()
            if not description:
                print("❌ Описание задачи не может быть пустым!")
                continue

            # Категория
            print("\n📂 Выберите категорию:")
            for idx, category in enumerate(categories, 1):
                print(f"{idx}. {category}")

            while True:
                try:
                    cat_choice = int(input(f"Ваш выбор (1-{len(categories)}): ").strip())
                    if 1 <= cat_choice <= len(categories):
                        selected_category = categories[cat_choice - 1]
                        break
                    else:
                        print(f"❌ Введите число от 1 до {len(categories)}")
                except ValueError:
                    print("❌ Пожалуйста, введите номер категории")

            # Приоритет
            print("\n🎯 Выберите приоритет:")
            for idx, priority in enumerate(priorities, 1):
                print(f"{idx}. {priority}")

            while True:
                try:
                    priority_choice = int(input(f"Ваш выбор (1-{len(priorities)}): ").strip())
                    if 1 <= priority_choice <= len(priorities):
                        selected_priority = priorities[priority_choice - 1]
                        break
                    else:
                        print(f"❌ Введите число от 1 до {len(priorities)}")
                except ValueError:
                    print("❌ Пожалуйста, введите номер приоритета")

            # Создание задачи
            new_task = {
                'описание': description,
                'сделана': False,
                'приоритет': selected_priority,
                'категория': selected_category,
                'дата_создания': datetime.now().strftime("%Y-%m-%d %H:%M"),
                'дата_выполнения': None
            }

            tasks.append(new_task)
            save_tasks(tasks)  # Автосохранение
            print(f"✅ Задача добавлена! Категория: {selected_category}, Приоритет: {selected_priority}")

        # 3. Удалить задачу
        elif choice == "3":
            print("\n" + "─" * 40)
            print("🗑️  УДАЛЕНИЕ ЗАДАЧИ")
            print("─" * 40)

            if not tasks:
                print("📭 Список задач пуст!")
                continue

            display_tasks(tasks, "ВЫБЕРИТЕ ЗАДАЧУ ДЛЯ УДАЛЕНИЯ", False)

            try:
                task_num = int(input(f"\nВведите номер задачи для удаления (1-{len(tasks)}): ").strip())
                if 1 <= task_num <= len(tasks):
                    removed = tasks.pop(task_num - 1)
                    save_tasks(tasks)  # Автосохранение
                    print(f"✅ Удалено: '{removed['описание']}'")
                else:
                    print(f"❌ Неверный номер!")
            except ValueError:
                print("❌ Ошибка! Введите номер.")

        # 4. Отметить задачу как выполненную
        elif choice == "4":
            print("\n" + "─" * 40)
            print("✅ ОТМЕТКА ЗАДАЧИ КАК ВЫПОЛНЕННОЙ")
            print("─" * 40)

            if not tasks:
                print("📭 Список задач пуст!")
                continue

            # Показываем только невыполненные
            undone = [task for task in tasks if not task['сделана']]

            if not undone:
                print("🎉 Все задачи уже выполнены!")
                continue

            display_tasks(undone, "НЕВЫПОЛНЕННЫЕ ЗАДАЧИ", False)

            try:
                task_num = int(input(f"\nВведите номер задачи для отметки (1-{len(undone)}): ").strip())
                if 1 <= task_num <= len(undone):
                    # Находим задачу в основном списке
                    undone_index = 0
                    for i, task in enumerate(tasks):
                        if not task['сделана']:
                            undone_index += 1
                            if undone_index == task_num:
                                tasks[i]['сделана'] = True
                                tasks[i]['дата_выполнения'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                                save_tasks(tasks)  # Автосохранение
                                print(f"✅ Задача выполнена: '{tasks[i]['описание']}'")
                                break
                else:
                    print(f"❌ Неверный номер!")
            except ValueError:
                print("❌ Ошибка! Введите номер.")

        # 5. Фильтры и категории
        elif choice == "5":
            print("\n" + "─" * 40)
            print("🔍 ФИЛЬТРЫ И КАТЕГОРИИ")
            print("─" * 40)

            while True:
                print("\n📊 ФИЛЬТРЫ:")
                print("1. Показать ВСЕ задачи")
                print("2. Показать ВЫПОЛНЕННЫЕ (сделано)")
                print("3. Показать НЕВЫПОЛНЕННЫЕ (не_сделано)")
                print("\n📂 КАТЕГОРИИ:")
                for idx, category in enumerate(categories, 1):
                    print(f"{idx + 3}. Показать {category.upper()}")
                print(f"{len(categories) + 4}. Назад в главное меню")

                filter_choice = input(f"\nВыберите фильтр (1-{len(categories) + 4}): ").strip()

                if filter_choice == "1":
                    display_tasks(tasks, "ВСЕ ЗАДАЧИ")
                elif filter_choice == "2":
                    filtered = filter_tasks(tasks, "сделано")
                    display_tasks(filtered, "ВЫПОЛНЕННЫЕ ЗАДАЧИ")
                elif filter_choice == "3":
                    filtered = filter_tasks(tasks, "не_сделано")
                    display_tasks(filtered, "НЕВЫПОЛНЕННЫЕ ЗАДАЧИ")
                elif filter_choice.isdigit() and 4 <= int(filter_choice) <= len(categories) + 3:
                    category_idx = int(filter_choice) - 4
                    if 0 <= category_idx < len(categories):
                        filtered = filter_tasks(tasks, categories[category_idx])
                        display_tasks(filtered, f"ЗАДАЧИ КАТЕГОРИИ: {categories[category_idx].upper()}")
                elif filter_choice == str(len(categories) + 4):
                    break
                else:
                    print("❌ Неверный выбор!")

        # 6. Выйти и сохранить
        elif choice == "6":
            print("\n" + "=" * 60)
            print("🚪 ВЫХОД ИЗ ПРИЛОЖЕНИЯ")
            print("=" * 60)

            # Автосохранение
            save_tasks(tasks)

            # Статистика
            if tasks:
                completed = sum(1 for task in tasks if task['сделана'])

                print("\n📈 ИТОГОВАЯ СТАТИСТИКА:")
                print(f"   📋 Всего задач: {len(tasks)}")
                print(f"   ✅ Выполнено: {completed}")
                print(f"   ⭕ Осталось: {len(tasks) - completed}")

                print("\n📊 РАСПРЕДЕЛЕНИЕ ПО КАТЕГОРИЯМ:")
                for category in categories:
                    cat_tasks = [t for t in tasks if t['категория'] == category]
                    if cat_tasks:
                        cat_completed = sum(1 for t in cat_tasks if t['сделана'])
                        print(f"   {category.capitalize():10}: {len(cat_tasks):3} задач "
                              f"({cat_completed:2} выполнено)")

                print("\n🎯 РАСПРЕДЕЛЕНИЕ ПО ПРИОРИТЕТАМ:")
                for priority in priorities:
                    pri_tasks = [t for t in tasks if t['приоритет'] == priority]
                    if pri_tasks:
                        pri_completed = sum(1 for t in pri_tasks if t['сделана'])
                        print(f"   {priority.capitalize():10}: {len(pri_tasks):3} задач "
                              f"({pri_completed:2} выполнено)")

            print("\n💾 Все задачи сохранены в файл tasks.json")
            print("🔄 При следующем запуске задачи будут загружены автоматически")
            print("=" * 60)
            break

        else:
            print("❌ Неверный выбор! Пожалуйста, выберите от 1 до 6.")


# Запуск приложения
if __name__ == "__main__":
    try:
        todo_list_app_pro()
    except KeyboardInterrupt:
        print("\n\n⚠️ Программа прервана пользователем.")
        print("Задачи автоматически сохраняются...")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")