'''
Этап 5: Оркестрация

Промпт 5:
```
Напиши main.py, который объединяет все модули системы мониторинга цен.

Алгоритм работы:
1. Загрузить конфиг
2. Инициализировать БД
3. Для каждого URL из конфига:
   - Получить текущую цену
   - Если цена изменилась, сохранить в историю
   - Если цена упала ниже порога, отправить уведомление
4. После обработки всех URL, отправить дневной отчет
5. Записать в лог время выполнения и количество обработанных товаров

Добавь возможность однократного запуска (для cron) и режима бесконечного цикла с интервалом из конфига.

Используй аргументы командной строки:
python main.py --once (однократный запуск)
python main.py --daemon (бесконечный цикл)
```
'''

import json
import os


class Config:
    """Класс для работы с конфигурацией"""

    def __init__(self, config_path='config.json'):
        self.config_path = config_path
        self.load_config()

    def load_config(self):
        """Загрузка конфигурации из JSON файла"""
        if not os.path.exists(self.config_path):
            # Создание конфигурации по умолчанию
            self.create_default_config()
            print(f"\n📝 Создан файл конфигурации: {self.config_path}")
            print("✏️ Отредактируйте его под свои нужды и запустите снова.\n")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Основные настройки
        self.urls = config.get('urls', [])
        self.check_interval = config.get('check_interval', 300)  # 5 минут для учебных целей
        self.db_path = os.path.join(
            'data', config.get('db_path', 'prices.db'))
        self.user_agent = config.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        self.timeout = config.get('timeout', 30)
        self.request_delay = config.get('request_delay', 2)
        self.verify_ssl = config.get('verify_ssl', False)  # Отключаем SSL для учебных сайтов
        self.use_mock_on_error = config.get('use_mock_on_error', True)  # Использовать тестовые данные при ошибках

        # Настройки уведомлений
        self.notification_config = config.get('notifications', {})

    def create_default_config(self):
        """Создание конфигурации по умолчанию с учебными сайтами"""
        default_config = {
            "urls": [
                {
                    "url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
                    "name": "A Light in the Attic (книга)",
                    "threshold": 50.00,
                    "price_selector": ".price_color",
                    "name_selector": "h1"
                },
                {
                    "url": "https://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html",
                    "name": "Tipping the Velvet (книга)",
                    "threshold": 45.00,
                    "price_selector": ".price_color",
                    "name_selector": "h1"
                },
                {
                    "url": "https://books.toscrape.com/catalogue/soumission_998/index.html",
                    "name": "Soumission (книга)",
                    "threshold": 55.00,
                    "price_selector": ".price_color",
                    "name_selector": "h1"
                },
                {
                    "url": "https://quotes.toscrape.com/",
                    "name": "Random Quote (цитаты)",
                    "threshold": 100.00,
                    "price_selector": ".text",
                    "name_selector": ".author"
                },
                {
                    "url": "https://httpbin.org/anything",
                    "name": "HTTP Test (тестовый)",
                    "threshold": 1000.00
                }
            ],
            "check_interval": 300,
            "db_path": "prices.db",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "timeout": 30,
            "request_delay": 2,
            "verify_ssl": False,
            "use_mock_on_error": True,
            "notifications": {
                "console": {
                    "enabled": True
                },
                "email": {
                    "enabled": False,
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "sender": "monitor@example.com",
                    "password": "your_password",
                    "recipients": ["user@example.com"]
                },
                "telegram": {
                    "enabled": False,
                    "bot_token": "YOUR_BOT_TOKEN",
                    "chat_id": "YOUR_CHAT_ID"
                }
            },
            "log_level": "INFO"
        }

        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)

        self._print_welcome_message()

    def _print_welcome_message(self):
        """Вывод приветственного сообщения"""
        print("""
╔══════════════════════════════════════════════════════════╗
║     📚 УЧЕБНЫЕ САЙТЫ ДЛЯ ТЕСТИРОВАНИЯ                   ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  1. books.toscrape.com                                   ║
║     📖 Демо-магазин книг с реальными ценами             ║
║                                                          ║
║  2. quotes.toscrape.com                                  ║
║     💬 Сайт с цитатами для тестирования парсинга        ║
║                                                          ║
║  3. httpbin.org                                          ║
║     🌐 Тестовый HTTP сервер                              ║
║                                                          ║
╠══════════════════════════════════════════════════════════╣
║     📁 Директории:                                       ║
║     📂 Логи: logs/                                       ║
║     📂 База данных: data/                                ║
╠══════════════════════════════════════════════════════════╣
║     🚀 Запуск:                                           ║
║     python main.py --once                                ║
║     python main.py --daemon                              ║
╚══════════════════════════════════════════════════════════╝
        """)