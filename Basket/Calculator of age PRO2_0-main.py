"""
КАЛЬКУЛЯТОР ВОЗРАСТА ПРО 2.0
Расширенная версия с графическим интерфейсом и дополнительными функциями
"""

# Импорт необходимых библиотек
import tkinter as tk  # Для создания графического интерфейса
from tkinter import ttk, messagebox, scrolledtext  # Дополнительные виджеты Tkinter
from datetime import datetime  # Для работы с датами и временем
import matplotlib.pyplot as plt  # Для создания графиков
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # Для встраивания графика в Tkinter
import json  # Для сохранения и загрузки данных в формате JSON
import os  # Для работы с файловой системой
import random  # Для случайного выбора знаменитостей


class AgeCalculatorPro:
    """
    Главный класс приложения - калькулятора возраста
    Содержит весь функционал и элементы интерфейса
    """

    def __init__(self, root):
        """
        Конструктор класса - инициализирует приложение
        root: главное окно Tkinter
        """
        self.root = root  # Сохраняем ссылку на главное окно
        self.root.title("Калькулятор Возраста PRO 2.0")  # Устанавливаем заголовок окна
        self.root.geometry("900x700")  # Устанавливаем размер окна (ширина x высота)
        self.root.configure(bg='#f0f8ff')  # Устанавливаем фоновый цвет окна (светло-голубой)

        # Словарь знаменитостей для сравнения (имя: год рождения)
        self.celebrities = {
            "Илон Маск": 1971,
            "Джефф Безос": 1964,
            "Билл Гейтс": 1955,
            "Марк Цукерберг": 1984,
            "Стив Джобс": 1955,
            "Павел Дуров": 1984,
            "Александр Пушкин": 1799,
            "Леонардо да Винчи": 1452,
            "Альберт Эйнштейн": 1879,
            "Юрий Гагарин": 1934,
            "Владимир Путин": 1952,
            "Илон Маск (папа)": 1946,
            "Тим Кук (Apple)": 1960,
            "Сергей Брин (Google)": 1973,
            "Ларри Пейдж (Google)": 1973,
            "Рид Хастингс (Netflix)": 1960,
            "Джек Ма (Alibaba)": 1964
        }

        # Имя файла для сохранения истории
        self.history_file = "age_history.json"

        # Загружаем историю из файла при запуске
        self.load_history()

        # Создаем все элементы интерфейса
        self.create_widgets()

        # Устанавливаем обработчик закрытия окна
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        """
        Создает все элементы графического интерфейса
        Располагает их в окне приложения
        """
        # Стиль для виджетов
        style = ttk.Style()
        style.configure('Title.TLabel', font=('Arial', 24, 'bold'), background='#f0f8ff')
        style.configure('Header.TLabel', font=('Arial', 14, 'bold'), background='#f0f8ff')
        style.configure('Result.TLabel', font=('Arial', 16), background='#f0f8ff', foreground='#2e8b57')

        # Заголовок приложения
        title_label = ttk.Label(
            self.root,
            text="🧮 КАЛЬКУЛЯТОР ВОЗРАСТА PRO 2.0",
            style='Title.TLabel'
        )
        title_label.pack(pady=20)  # Размещаем с отступом 20 пикселей сверху

        # Основной фрейм (контейнер) для ввода данных
        input_frame = tk.Frame(self.root, bg='#e6f3ff', padx=20, pady=20, relief=tk.RAISED, bd=2)
        input_frame.pack(pady=10, fill=tk.X, padx=20)

        # Метка (подпись) для поля ввода
        birth_label = ttk.Label(
            input_frame,
            text="Введите ваш год рождения:",
            font=('Arial', 12),
            background='#e6f3ff'
        )
        birth_label.grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)

        # Поле для ввода года рождения
        self.birth_year_entry = tk.Entry(
            input_frame,
            font=('Arial', 12),
            width=20,
            justify=tk.CENTER
        )
        self.birth_year_entry.grid(row=0, column=1, padx=10, pady=10)
        self.birth_year_entry.focus()  # Устанавливаем фокус на поле ввода

        # Кнопка для расчета возраста
        self.calculate_button = tk.Button(
            input_frame,
            text="🎯 Рассчитать возраст",
            font=('Arial', 12, 'bold'),
            bg='#4CAF50',  # Зеленый цвет
            fg='white',
            command=self.calculate_age,  # Привязываем функцию обработки
            padx=20,
            pady=10,
            cursor='hand2'  # Меняем курсор при наведении
        )
        self.calculate_button.grid(row=0, column=2, padx=10, pady=10)

        # Метка для отображения текущего года
        current_year = datetime.now().year
        year_label = ttk.Label(
            input_frame,
            text=f"Текущий год: {current_year}",
            font=('Arial', 10, 'italic'),
            background='#e6f3ff',
            foreground='#666666'
        )
        year_label.grid(row=1, column=0, columnspan=3, pady=5)

        # Фрейм для отображения результатов
        result_frame = tk.Frame(self.root, bg='#ffffff', padx=20, pady=20, relief=tk.GROOVE, bd=2)
        result_frame.pack(pady=20, fill=tk.X, padx=20)

        # Метка для отображения возраста
        self.result_label = ttk.Label(
            result_frame,
            text="Ваш возраст появится здесь",
            style='Result.TLabel'
        )
        self.result_label.pack(pady=10)

        # Метка для дополнительной информации
        self.details_label = ttk.Label(
            result_frame,
            text="",
            font=('Arial', 11),
            background='#ffffff',
            wraplength=600  # Автоматический перенос текста
        )
        self.details_label.pack(pady=5)

        # Фрейм для кнопок дополнительных функций
        buttons_frame = tk.Frame(self.root, bg='#f0f8ff', pady=10)
        buttons_frame.pack()

        # Создаем кнопки дополнительных функций
        button_configs = [
            ("📊 Показать график", self.show_graph, '#2196F3'),  # Синий
            ("⭐ Сравнить со знаменитостями", self.compare_celebrities, '#FF9800'),  # Оранжевый
            ("💾 Сохранить результат", self.save_result, '#9C27B0'),  # Фиолетовый
            ("📋 История расчетов", self.show_history, '#607D8B'),  # Серый
            ("🧹 Очистить историю", self.clear_history, '#F44336'),  # Красный
        ]

        # Создаем кнопки в цикле
        for i, (text, command, color) in enumerate(button_configs):
            btn = tk.Button(
                buttons_frame,
                text=text,
                font=('Arial', 10, 'bold'),
                bg=color,
                fg='white',
                command=command,
                padx=15,
                pady=8,
                cursor='hand2'
            )
            btn.grid(row=0, column=i, padx=5, pady=5)

        # Область для отображения сравнения со знаменитостями
        self.comparison_text = scrolledtext.ScrolledText(
            self.root,
            height=8,
            width=80,
            font=('Arial', 10),
            wrap=tk.WORD,
            bg='#f9f9f9'
        )
        self.comparison_text.pack(pady=10, padx=20)
        self.comparison_text.insert(tk.END, "Здесь появится сравнение со знаменитостями...\n")
        self.comparison_text.config(state=tk.DISABLED)  # Делаем текстовое поле только для чтения

    def calculate_age(self):
        """
        Основная функция расчета возраста
        Выполняет проверку ввода и вычисляет возраст
        """
        # Получаем текст из поля ввода и удаляем лишние пробелы
        birth_year_input = self.birth_year_entry.get().strip()

        # Проверка на пустой ввод
        if not birth_year_input:
            messagebox.showerror("Ошибка", "Пожалуйста, введите год рождения!")
            return

        try:
            # Пытаемся преобразовать ввод в целое число
            birth_year = int(birth_year_input)
            current_year = datetime.now().year  # Получаем текущий год

            # Проверка на корректность года
            if birth_year <= 0:
                messagebox.showerror("Ошибка", "Год должен быть положительным числом!")
                return

            if birth_year > current_year:
                messagebox.showerror("Ошибка", f"Год рождения не может быть больше {current_year}!")
                return

            # Проверка на нереалистичный возраст (>150 лет)
            if birth_year < current_year - 150:
                response = messagebox.askyesno(
                    "Проверка",
                    f"Вы уверены? Если вы родились в {birth_year} году, вам больше 150 лет.\nВсё равно продолжить?"
                )
                if not response:
                    return

            # Вычисляем возраст
            age = current_year - birth_year

            # Определяем правильное склонение слова "год"
            year_word = self.get_year_word(age)

            # Обновляем метку с результатом
            self.result_label.config(
                text=f"🎉 ВАШ ВОЗРАСТ: {age} {year_word}",
                foreground='#2e8b57'  # Зеленый цвет для успешного результата
            )

            # Формируем детальную информацию
            details = (
                f"📅 Год рождения: {birth_year}\n"
                f"📅 Текущий год: {current_year}\n"
                f"🔮 Через 5 лет вам будет: {age + 5} {self.get_year_word(age + 5)}\n"
                f"🌟 Поколение: {self.get_generation(birth_year)}"
            )
            self.details_label.config(text=details)

            # Сохраняем результат для использования в других функциях
            self.current_result = {
                'birth_year': birth_year,
                'age': age,
                'calculation_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # Автоматически выполняем сравнение со знаменитостями
            self.compare_celebrities()

            # Добавляем в историю
            self.add_to_history(self.current_result)

        except ValueError:
            # Обработка случая, когда введен не число
            messagebox.showerror("Ошибка", "Пожалуйста, введите число (например, 1990)!")
        except Exception as e:
            # Обработка любых других ошибок
            messagebox.showerror("Ошибка", f"Произошла ошибка: {str(e)}")

    def get_year_word(self, age):
        """
        Возвращает правильное склонение слова 'год' для заданного возраста
        age: возраст для которого нужно определить склонение
        Возвращает: строку 'год', 'года' или 'лет'
        """
        # Правила русского языка для склонения слова "год"
        if age % 10 == 1 and age % 100 != 11:
            return "год"
        elif age % 10 in [2, 3, 4] and age % 100 not in [12, 13, 14]:
            return "года"
        else:
            return "лет"

    def get_generation(self, birth_year):
        """
        Определяет поколение по году рождения
        birth_year: год рождения для анализа
        Возвращает: название поколения
        """
        # Определяем поколение по диапазонам годов
        if 1928 <= birth_year <= 1945:
            return "Молчаливое поколение"
        elif 1946 <= birth_year <= 1964:
            return "Бэби-бумеры"
        elif 1965 <= birth_year <= 1980:
            return "Поколение X"
        elif 1981 <= birth_year <= 1996:
            return "Поколение Y (Миллениалы)"
        elif 1997 <= birth_year <= 2012:
            return "Поколение Z (Зумеры)"
        elif birth_year >= 2013:
            return "Поколение Alpha"
        else:
            return "Особое поколение"

    def compare_celebrities(self):
        """
        Сравнивает возраст пользователя с возрастом знаменитостей
        Выбирает 5 случайных знаменитостей и показывает разницу в возрасте
        """
        # Проверяем, есть ли текущий результат для сравнения
        if not hasattr(self, 'current_result'):
            messagebox.showwarning("Внимание", "Сначала рассчитайте свой возраст!")
            return

        user_birth_year = self.current_result['birth_year']
        user_age = self.current_result['age']

        # Выбираем 5 случайных знаменитостей из словаря
        selected_celebrities = random.sample(list(self.celebrities.items()), min(5, len(self.celebrities)))

        # Включаем текущий год в расчеты
        current_year = datetime.now().year

        # Очищаем текстовое поле и активируем его для записи
        self.comparison_text.config(state=tk.NORMAL)
        self.comparison_text.delete(1.0, tk.END)

        # Заголовок сравнения
        self.comparison_text.insert(tk.END, "🌟 СРАВНЕНИЕ СО ЗНАМЕНИТОСТЯМИ 🌟\n")
        self.comparison_text.insert(tk.END, "=" * 50 + "\n\n")

        # Добавляем сравнение для каждой выбранной знаменитости
        for name, celeb_birth_year in selected_celebrities:
            celeb_age = current_year - celeb_birth_year
            age_difference = user_age - celeb_age

            if age_difference > 0:
                comparison = f"старше на {abs(age_difference)} {self.get_year_word(abs(age_difference))}"
            elif age_difference < 0:
                comparison = f"моложе на {abs(age_difference)} {self.get_year_word(abs(age_difference))}"
            else:
                comparison = "одного возраста"

            # Форматируем и выводим информацию о знаменитости
            self.comparison_text.insert(tk.END,
                                        f"• {name} (род. {celeb_birth_year}): {celeb_age} {self.get_year_word(celeb_age)}\n"
                                        f"  → Вы {comparison} с ним/ней\n\n"
                                        )

        # Добавляем интересные факты
        self.comparison_text.insert(tk.END, "📊 ИНТЕРЕСНЫЕ ФАКТЫ:\n")

        # Находим самого старшего и самого младшего из всех знаменитостей
        oldest_celeb = max(self.celebrities.items(), key=lambda x: current_year - x[1])
        youngest_celeb = min(self.celebrities.items(), key=lambda x: current_year - x[1])

        self.comparison_text.insert(tk.END,
                                    f"• Самый старший в списке: {oldest_celeb[0]} ({oldest_celeb[1]} г.р.)\n"
                                    f"• Самый младший в списке: {youngest_celeb[0]} ({youngest_celeb[1]} г.р.)\n"
                                    )

        # Делаем текстовое поле снова только для чтения
        self.comparison_text.config(state=tk.DISABLED)

    def show_graph(self):
        """
        Создает и отображает график изменения возраста с течением времени
        Показывает прогноз на будущие годы
        """
        # Проверяем, есть ли текущий результат для построения графика
        if not hasattr(self, 'current_result'):
            messagebox.showwarning("Внимание", "Сначала рассчитайте свой возраст!")
            return

        birth_year = self.current_result['birth_year']
        current_year = datetime.now().year

        # Создаем новое окно для графика
        graph_window = tk.Toplevel(self.root)
        graph_window.title("График изменения возраста")
        graph_window.geometry("800x600")

        # Создаем фигуру для графика
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

        # Подграфик 1: Возраст по годам
        years = list(range(birth_year, current_year + 10))  # От года рождения до +10 лет вперед
        ages = [year - birth_year for year in years]

        # Разделяем на прошлое и будущее
        past_years = [year for year in years if year <= current_year]
        past_ages = ages[:len(past_years)]

        future_years = [year for year in years if year > current_year]
        future_ages = ages[len(past_years):]

        # График для прошлых лет
        ax1.plot(past_years, past_ages, 'b-o', linewidth=2, markersize=4, label='Прошлые годы')

        # График для будущих лет (прогноз)
        if future_years:
            ax1.plot(future_years, future_ages, 'r--o', linewidth=2, markersize=4, label='Будущие годы')

        # Выделяем текущий год
        ax1.axvline(x=current_year, color='g', linestyle=':', linewidth=2, label='Текущий год')
        ax1.axhline(y=self.current_result['age'], color='g', linestyle=':', linewidth=1)

        ax1.set_xlabel('Год', fontsize=12)
        ax1.set_ylabel('Возраст (лет)', fontsize=12)
        ax1.set_title(f'Изменение возраста с {birth_year} года', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend()

        # Подграфик 2: Сравнение с поколениями
        generations = {
            'Молчаливое': (1928, 1945),
            'Бэби-бумеры': (1946, 1964),
            'Поколение X': (1965, 1980),
            'Миллениалы': (1981, 1996),
            'Поколение Z': (1997, 2012),
            'Alpha': (2013, 2023)
        }

        colors = plt.cm.Set3(np.linspace(0, 1, len(generations)))

        for i, (name, (start, end)) in enumerate(generations.items()):
            ax2.barh(name, end - start, left=start, height=0.5, color=colors[i], alpha=0.7)
            if start <= birth_year <= end:
                ax2.barh(name, 1, left=birth_year - 0.5, height=0.5, color='red', alpha=0.9, label='Ваш год рождения')

        ax2.axvline(x=birth_year, color='red', linestyle='--', linewidth=2, label='Ваш год рождения')
        ax2.set_xlabel('Год рождения', fontsize=12)
        ax2.set_title('Поколения по годам рождения', fontsize=14, fontweight='bold')
        ax2.legend()

        # Настраиваем компоновку
        plt.tight_layout()

        # Встраиваем график в окно Tkinter
        canvas = FigureCanvasTkAgg(fig, master=graph_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Кнопка для сохранения графика
        save_button = tk.Button(
            graph_window,
            text="💾 Сохранить график",
            command=lambda: self.save_graph(fig),
            bg='#4CAF50',
            fg='white',
            font=('Arial', 10)
        )
        save_button.pack(pady=10)

    def save_graph(self, fig):
        """
        Сохраняет график в файл
        fig: объект графика matplotlib для сохранения
        """
        try:
            # Генерируем имя файла с текущей датой
            filename = f"возраст_график_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            fig.savefig(filename, dpi=300, bbox_inches='tight')
            messagebox.showinfo("Успех", f"График сохранен в файл:\n{filename}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить график: {str(e)}")

    def save_result(self):
        """
        Сохраняет текущий результат расчета в текстовый файл
        """
        if not hasattr(self, 'current_result'):
            messagebox.showwarning("Внимание", "Сначала рассчитайте свой возраст!")
            return

        try:
            # Генерируем имя файла с текущей датой
            filename = f"возраст_результат_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

            # Создаем содержимое файла
            content = f"""РЕЗУЛЬТАТ РАСЧЕТА ВОЗРАСТА
==============================
Дата расчета: {self.current_result['calculation_date']}
Год рождения: {self.current_result['birth_year']}
Текущий возраст: {self.current_result['age']} {self.get_year_word(self.current_result['age'])}
Поколение: {self.get_generation(self.current_result['birth_year'])}

Дополнительная информация:
• Через 5 лет: {self.current_result['age'] + 5} {self.get_year_word(self.current_result['age'] + 5)}
• В 2030 году: {2030 - self.current_result['birth_year']} {self.get_year_word(2030 - self.current_result['birth_year'])}
• В 2050 году: {2050 - self.current_result['birth_year']} {self.get_year_word(2050 - self.current_result['birth_year'])}

Сохранено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

            # Записываем в файл
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)

            messagebox.showinfo("Успех", f"Результат сохранен в файл:\n{filename}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить результат: {str(e)}")

    def add_to_history(self, result):
        """
        Добавляет результат расчета в историю
        result: словарь с результатами расчета
        """
        # Добавляем результат в историю
        self.history.append(result)

        # Сохраняем историю в файл
        self.save_history()

    def load_history(self):
        """
        Загружает историю расчетов из JSON файла
        Если файла нет - создает пустую историю
        """
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
            else:
                self.history = []
        except Exception as e:
            print(f"Ошибка загрузки истории: {e}")
            self.history = []

    def save_history(self):
        """
        Сохраняет историю расчетов в JSON файл
        """
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения истории: {e}")

    def show_history(self):
        """
        Показывает историю всех расчетов в новом окне
        """
        if not self.history:
            messagebox.showinfo("История", "История расчетов пуста!")
            return

        # Создаем новое окно для истории
        history_window = tk.Toplevel(self.root)
        history_window.title("История расчетов")
        history_window.geometry("600x400")

        # Создаем текстовое поле с прокруткой
        history_text = scrolledtext.ScrolledText(
            history_window,
            width=70,
            height=20,
            font=('Arial', 10)
        )
        history_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Добавляем заголовок
        history_text.insert(tk.END, "📋 ИСТОРИЯ РАСЧЕТОВ ВОЗРАСТА\n")
        history_text.insert(tk.END, "=" * 50 + "\n\n")

        # Добавляем каждый результат из истории
        for i, record in enumerate(reversed(self.history[-20:]), 1):  # Последние 20 записей
            history_text.insert(tk.END,
                                f"{i}. {record['calculation_date']}\n"
                                f"   Год рождения: {record['birth_year']}\n"
                                f"   Возраст: {record['age']} {self.get_year_word(record['age'])}\n"
                                f"   {'─' * 30}\n\n"
                                )

        # Делаем текстовое поле только для чтения
        history_text.config(state=tk.DISABLED)

        # Кнопка для очистки истории
        clear_button = tk.Button(
            history_window,
            text="🧹 Очистить историю",
            command=self.clear_history,
            bg='#F44336',
            fg='white',
            font=('Arial', 10)
        )
        clear_button.pack(pady=10)

    def clear_history(self):
        """
        Очищает всю историю расчетов после подтверждения
        """
        if not self.history:
            messagebox.showinfo("История", "История уже пуста!")
            return

        # Запрашиваем подтверждение
        response = messagebox.askyesno(
            "Подтверждение",
            "Вы уверены, что хотите очистить всю историю расчетов?\nЭто действие нельзя отменить."
        )

        if response:
            self.history = []
            self.save_history()
            messagebox.showinfo("Успех", "История расчетов очищена!")

    def on_closing(self):
        """
        Обработчик закрытия окна
        Сохраняет данные и корректно завершает программу
        """
        # Сохраняем историю при выходе
        self.save_history()
        self.root.destroy()


# Точка входа в программу
def main():
    """
    Главная функция, запускающая приложение
    """
    try:
        # Импортируем numpy для графика поколений (только если нужно)
        global np
        import numpy as np

        # Создаем главное окно Tkinter
        root = tk.Tk()

        # Создаем экземпляр нашего приложения
        app = AgeCalculatorPro(root)

        # Запускаем главный цикл обработки событий
        root.mainloop()

    except ImportError as e:
        # Обработка ошибки импорта библиотек
        print(f"Ошибка импорта библиотек: {e}")
        print("Установите необходимые библиотеки:")
        print("pip install matplotlib numpy")
    except Exception as e:
        # Обработка любых других ошибок
        print(f"Критическая ошибка: {e}")


# Запускаем программу, если файл запущен напрямую
if __name__ == "__main__":
    main()