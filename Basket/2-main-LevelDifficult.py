import random


def guess_number_game():
    """Основная функция игры с уровнями сложности"""

    # Настройки уровней сложности
    DIFFICULTY_SETTINGS = {
        '1': {'name': 'Новичок', 'attempts': float('inf'), 'range': 20, 'hints': True},
        '2': {'name': 'Средний', 'attempts': 10, 'range': 50, 'hints': True},
        '3': {'name': 'Сложный', 'attempts': 3, 'range': 100, 'hints': False}
    }

    def display_rules():
        """Отображение правил игры"""
        print("=" * 50)
        print("           ИГРА 'УГАДАЙ ЧИСЛО' - ПРОФИ ВЕРСИЯ")
        print("=" * 50)
        print("\n🎯 Уровни сложности:")
        for key, settings in DIFFICULTY_SETTINGS.items():
            attempts_text = "∞" if settings['attempts'] == float('inf') else settings['attempts']
            print(f"   {key}. {settings['name']:10} - {attempts_text:>2} попыток | Диапазон: 1-{settings['range']}")
        print("\n📊 Особенности:")
        print("   • На уровнях 'Новичок' и 'Средний' есть подсказки 'Больше/Меньше'")
        print("   • На уровне 'Сложный' подсказки отключены!")
        print("=" * 50)

    def select_difficulty():
        """Выбор уровня сложности"""
        while True:
            print("\n" + "═" * 30)
            choice = input("Выберите уровень сложности (1-3): ").strip()

            if choice in DIFFICULTY_SETTINGS:
                settings = DIFFICULTY_SETTINGS[choice]
                print(f"\n✅ Выбран уровень: {settings['name']}")
                print(f"📊 Диапазон чисел: 1-{settings['range']}")
                print(f"🎯 Доступно попыток: {'∞' if settings['attempts'] == float('inf') else settings['attempts']}")
                print(f"💡 Подсказки: {'ВКЛ' if settings['hints'] else 'ВЫКЛ'}")
                return settings
            else:
                print("❌ Пожалуйста, выберите 1, 2 или 3")

    def play_round(settings):
        """Игровой раунд с выбранными настройками"""
        secret_number = random.randint(1, settings['range'])
        max_attempts = settings['attempts']
        remaining_attempts = max_attempts
        attempts_made = 0

        print(f"\n{'🚀 НАЧАЛО РАУНДА ' + '🚀' * 3}")
        print(f"Я загадал число от 1 до {settings['range']}")

        while remaining_attempts > 0:
            # Отображение оставшихся попыток
            if max_attempts != float('inf'):
                print(f"\n🔄 Попытка #{attempts_made + 1} | Осталось: {remaining_attempts}")
                print("─" * 30)
            else:
                print(f"\n🔄 Попытка #{attempts_made + 1} (бесконечный режим)")
                print("─" * 30)

            # Ввод пользователя
            try:
                guess = int(input("Ваша догадка: "))
                attempts_made += 1

                # Проверка диапазона
                if guess < 1 or guess > settings['range']:
                    print(f"⚠️ Число должно быть от 1 до {settings['range']}!")
                    if max_attempts != float('inf'):
                        remaining_attempts -= 1
                    continue

                # Проверка угадывания
                if guess == secret_number:
                    print(f"\n{'🎉' * 5} ПОБЕДА! {'🎉' * 5}")
                    print(f"Вы угадали число {secret_number}!")
                    print(f"Потрачено попыток: {attempts_made}")

                    # Бонусная система
                    if max_attempts != float('inf'):
                        efficiency = (max_attempts - attempts_made) / max_attempts * 100
                        print(f"Эффективность: {efficiency:.1f}%")
                    return True

                # Подсказки (если включены)
                if settings['hints']:
                    if guess < secret_number:
                        print("⬆️  Больше!")
                    else:
                        print("⬇️  Меньше!")
                else:
                    print("❓ Не угадали! (подсказки отключены)")

                # Уменьшение счетчика попыток
                if max_attempts != float('inf'):
                    remaining_attempts -= 1

                    # Предупреждения
                    if remaining_attempts == 2:
                        print("⚠️  Осторожно! Осталось всего 2 попытки!")
                    elif remaining_attempts == 1:
                        print("🔥  ПОСЛЕДНИЙ ШАНС! Будьте точны!")

            except ValueError:
                print("❌ Ошибка! Введите целое число.")
                if max_attempts != float('inf'):
                    remaining_attempts -= 1

        # Если попытки закончились
        print(f"\n{'💀' * 5} ПРОИГРЫШ {'💀' * 5}")
        print(f"Вы исчерпали все попытки!")
        print(f"Загаданное число было: {secret_number}")
        return False

    def play_again():
        """Спросить о повторной игре"""
        while True:
            print("\n" + "═" * 40)
            choice = input("Сыграем еще раз? (да/нет): ").lower().strip()

            if choice in ['да', 'д', 'yes', 'y', '+']:
                return True
            elif choice in ['нет', 'н', 'no', 'n', '-']:
                print("\n" + "=" * 50)
                print("        Спасибо за игру! Возвращайтесь!")
                print("=" * 50)
                return False
            else:
                print("❌ Пожалуйста, ответьте 'да' или 'нет'")

    # Главный цикл игры
    print("\n" + "✨" * 25)
    print("ДОБРО ПОЖАЛОВАТЬ В 'УГАДАЙ ЧИСЛО'!")
    print("✨" * 25)

    while True:
        # Показ правил и выбор сложности
        display_rules()
        settings = select_difficulty()

        # Игровой процесс
        victory = play_round(settings)

        # Статистика
        print("\n" + "📈" * 25)
        if victory:
            print("         Отличный результат!")
        else:
            print("         Не повезло в этот раз...")

        # Повтор игры
        if not play_again():
            break


# Запуск игры
if __name__ == "__main__":
    guess_number_game()