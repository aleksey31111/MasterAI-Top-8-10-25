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

import sqlite3
from datetime import datetime
import os


class Database:
    """Класс для работы с базой данных"""

    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None

    def initialize(self):
        """Инициализация базы данных"""
        # Создание директории для БД
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

        cursor = self.conn.cursor()

        # Таблица для истории цен
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                product_name TEXT,
                price REAL NOT NULL,
                currency TEXT DEFAULT 'RUB',
                is_mock BOOLEAN DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица для изменений цен
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                product_name TEXT,
                old_price REAL,
                new_price REAL,
                change_percent REAL,
                currency TEXT DEFAULT 'RUB',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица для уведомлений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                product_name TEXT,
                price REAL,
                threshold REAL,
                notification_type TEXT,
                sent_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Индексы
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_url ON price_history(url)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON price_history(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_changes_url ON price_changes(url)')

        self.conn.commit()

    def save_price(self, url, price, product_name=None, currency='RUB', is_mock=False):
        """Сохранение цены в историю"""
        cursor = self.conn.cursor()

        # Получение последней цены
        last_price = self.get_last_price(url)

        # Сохранение текущей цены
        cursor.execute('''
            INSERT INTO price_history (url, product_name, price, currency, is_mock)
            VALUES (?, ?, ?, ?, ?)
        ''', (url, product_name, price, currency, is_mock))

        # Если цена изменилась, записываем изменение
        if last_price is not None and abs(last_price - price) > 0.01:
            change_percent = ((price - last_price) / last_price) * 100
            cursor.execute('''
                INSERT INTO price_changes (url, product_name, old_price, new_price, change_percent, currency)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (url, product_name, last_price, price, change_percent, currency))

        self.conn.commit()
        return cursor.lastrowid

    def save_notification(self, url, product_name, price, threshold):
        """Сохранение информации об уведомлении"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO notifications (url, product_name, price, threshold, notification_type)
            VALUES (?, ?, ?, ?, ?)
        ''', (url, product_name, price, threshold, 'price_alert'))
        self.conn.commit()

    def get_last_price(self, url):
        """Получение последней цены для URL"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT price FROM price_history
            WHERE url = ?
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (url,))

        result = cursor.fetchone()
        return result[0] if result else None

    def get_price_history(self, url, limit=10):
        """Получение истории цен для URL"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT price, currency, timestamp, is_mock FROM price_history
            WHERE url = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (url, limit))

        return cursor.fetchall()

    def get_price_changes(self, url, limit=10):
        """Получение истории изменений цен"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT old_price, new_price, change_percent, currency, timestamp
            FROM price_changes
            WHERE url = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (url, limit))

        return cursor.fetchall()

    def get_today_stats(self):
        """Получение статистики за сегодня"""
        cursor = self.conn.cursor()
        today = datetime.now().date()

        # ИСПРАВЛЕННЫЙ ЗАПРОС - убираем LEFT JOIN price_changes
        cursor.execute('''
            SELECT 
                COUNT(DISTINCT url) as products_checked,
                COUNT(*) as total_checks,
                SUM(CASE WHEN is_mock = 1 THEN 1 ELSE 0 END) as mock_checks
            FROM price_history
            WHERE DATE(timestamp) = DATE(?)
        ''', (today.isoformat(),))

        stats = cursor.fetchone()

        # Отдельный запрос для количества изменений
        cursor.execute('''
            SELECT COUNT(*) as price_changes,
                   AVG(ABS(change_percent)) as avg_change_percent
            FROM price_changes
            WHERE DATE(timestamp) = DATE(?)
        ''', (today.isoformat(),))

        changes_stats = cursor.fetchone()

        # Объединяем результаты
        return (
            stats[0] or 0,  # products_checked
            stats[1] or 0,  # total_checks
            stats[2] or 0,  # mock_checks
            changes_stats[0] or 0,  # price_changes
            changes_stats[1] or 0  # avg_change_percent
        )

    def get_all_products(self):
        """Получение списка всех отслеживаемых товаров"""
        cursor = self.conn.cursor()

        # ИСПРАВЛЕННЫЙ ЗАПРОС - используем подзапросы вместо JOIN
        cursor.execute('''
            SELECT DISTINCT url, 
                   (SELECT product_name FROM price_history ph2 
                    WHERE ph2.url = ph1.url 
                    ORDER BY timestamp DESC LIMIT 1) as last_name,
                   (SELECT price FROM price_history ph2 
                    WHERE ph2.url = ph1.url 
                    ORDER BY timestamp DESC LIMIT 1) as last_price,
                   (SELECT currency FROM price_history ph2 
                    WHERE ph2.url = ph1.url 
                    ORDER BY timestamp DESC LIMIT 1) as currency,
                   (SELECT timestamp FROM price_history ph2 
                    WHERE ph2.url = ph1.url 
                    ORDER BY timestamp DESC LIMIT 1) as last_check
            FROM price_history ph1
            GROUP BY url
            ORDER BY last_check DESC
        ''')

        return cursor.fetchall()

    def get_product_with_changes(self, url):
        """Получение информации о товаре с последними изменениями"""
        cursor = self.conn.cursor()

        # Информация о товаре
        cursor.execute('''
            SELECT url, product_name, price, currency, timestamp, is_mock
            FROM price_history
            WHERE url = ?
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (url,))

        product = cursor.fetchone()

        # Последние изменения
        cursor.execute('''
            SELECT old_price, new_price, change_percent, timestamp
            FROM price_changes
            WHERE url = ?
            ORDER BY timestamp DESC
            LIMIT 5
        ''', (url,))

        changes = cursor.fetchall()

        return {
            'product': product,
            'changes': changes
        }

    def close(self):
        """Закрытие соединения с БД"""
        if self.conn:
            self.conn.close()