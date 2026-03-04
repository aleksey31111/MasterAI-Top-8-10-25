#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Этап 3: База данных

Промпт 3:
```
Напиши модуль database.py для системы мониторинга цен.

Требования к БД (SQLite):
- Таблица products: id, url, name, threshold_price
- Таблица price_history: id, product_id, price, timestamp

Функции:
1. init_db() - создает таблицы, если их нет
2. add_product(url, name, threshold) - добавляет новый товар
3. get_all_products() - возвращает список всех товаров
4. save_price(product_id, price) - записывает цену в историю
5. get_last_price(product_id) - получает последнюю цену
6. get_price_history(product_id, days=30) - историю для графиков

Все функции должны быть с обработкой ошибок и логированием.
```
'''

"""
Модуль для работы с базой данных SQLite в системе мониторинга цен.
Содержит простые функции для работы с товарами и историей цен.
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import os

# Настройка логирования
logger = logging.getLogger(__name__)

# Константы
DB_PATH = "prices.db"


class DatabaseError(Exception):
    """Исключение для ошибок базы данных"""
    pass


def get_connection():
    """
    Создает и возвращает соединение с базой данных.

    Returns:
        sqlite3.Connection: Объект соединения с БД
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Позволяет обращаться по именам колонок
        return conn
    except sqlite3.Error as e:
        logger.error(f"Ошибка подключения к БД: {e}")
        raise DatabaseError(f"Не удалось подключиться к БД: {e}")


# ========== ИНИЦИАЛИЗАЦИЯ ==========

def init_db() -> bool:
    """
    Создает таблицы в базе данных, если их еще нет.

    Returns:
        bool: True если инициализация прошла успешно
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # Создаем таблицу товаров
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    threshold_price REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Создаем таблицу истории цен
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    price REAL NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
                )
            """)

            # Создаем индексы для ускорения запросов
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_price_history_product_id 
                ON price_history(product_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_price_history_timestamp 
                ON price_history(timestamp)
            """)

            conn.commit()
            logger.info("База данных успешно инициализирована")
            return True

    except sqlite3.Error as e:
        logger.error(f"Ошибка при инициализации БД: {e}")
        return False
    except Exception as e:
        logger.error(f"Неожиданная ошибка при инициализации БД: {e}")
        return False


# ========== РАБОТА С ТОВАРАМИ ==========

def add_product(url: str, name: str, threshold: float) -> Optional[int]:
    """
    Добавляет новый товар в базу данных.

    Args:
        url: URL страницы товара
        name: Название товара
        threshold: Пороговая цена для уведомлений

    Returns:
        Optional[int]: ID добавленного товара или None в случае ошибки
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # Проверяем, существует ли уже такой URL
            cursor.execute("SELECT id FROM products WHERE url = ?", (url,))
            existing = cursor.fetchone()

            if existing:
                logger.warning(f"Товар с URL {url} уже существует (ID: {existing['id']})")
                return existing['id']

            # Добавляем новый товар
            cursor.execute("""
                INSERT INTO products (url, name, threshold_price)
                VALUES (?, ?, ?)
            """, (url, name, threshold))

            product_id = cursor.lastrowid
            conn.commit()

            logger.info(f"Добавлен товар ID {product_id}: {name} (порог: {threshold})")
            return product_id

    except sqlite3.IntegrityError as e:
        logger.error(f"Ошибка целостности при добавлении товара: {e}")
        return None
    except sqlite3.Error as e:
        logger.error(f"Ошибка БД при добавлении товара: {e}")
        return None
    except Exception as e:
        logger.error(f"Неожиданная ошибка при добавлении товара: {e}")
        return None


def get_all_products() -> List[Dict]:
    """
    Возвращает список всех товаров из базы данных.

    Returns:
        List[Dict]: Список товаров с полями id, url, name, threshold_price, created_at
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, url, name, threshold_price, created_at
                FROM products
                ORDER BY id
            """)

            products = [dict(row) for row in cursor.fetchall()]
            logger.debug(f"Получено товаров: {len(products)}")
            return products

    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении списка товаров: {e}")
        return []
    except Exception as e:
        logger.error(f"Неожиданная ошибка при получении товаров: {e}")
        return []


def get_product(product_id: int) -> Optional[Dict]:
    """
    Получает информацию о конкретном товаре по ID.

    Args:
        product_id: ID товара

    Returns:
        Optional[Dict]: Информация о товаре или None
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, url, name, threshold_price, created_at
                FROM products
                WHERE id = ?
            """, (product_id,))

            row = cursor.fetchone()
            return dict(row) if row else None

    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении товара {product_id}: {e}")
        return None


def delete_product(product_id: int) -> bool:
    """
    Удаляет товар и всю его историю цен.

    Args:
        product_id: ID товара

    Returns:
        bool: True если удаление успешно
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # Проверяем, существует ли товар
            cursor.execute("SELECT id FROM products WHERE id = ?", (product_id,))
            if not cursor.fetchone():
                logger.warning(f"Товар с ID {product_id} не найден")
                return False

            # Удаляем товар (история цен удалится каскадно)
            cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
            conn.commit()

            logger.info(f"Удален товар ID {product_id}")
            return True

    except sqlite3.Error as e:
        logger.error(f"Ошибка при удалении товара {product_id}: {e}")
        return False


# ========== РАБОТА С ИСТОРИЕЙ ЦЕН ==========

def save_price(product_id: int, price: float) -> bool:
    """
    Сохраняет цену товара в историю.

    Args:
        product_id: ID товара
        price: Текущая цена

    Returns:
        bool: True если сохранение успешно
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # Проверяем, существует ли товар
            cursor.execute("SELECT id FROM products WHERE id = ?", (product_id,))
            if not cursor.fetchone():
                logger.error(f"Товар с ID {product_id} не найден")
                return False

            # Сохраняем цену
            cursor.execute("""
                INSERT INTO price_history (product_id, price)
                VALUES (?, ?)
            """, (product_id, price))

            conn.commit()
            logger.debug(f"Сохранена цена {price} для товара {product_id}")
            return True

    except sqlite3.Error as e:
        logger.error(f"Ошибка при сохранении цены для товара {product_id}: {e}")
        return False


def get_last_price(product_id: int) -> Optional[float]:
    """
    Получает последнюю известную цену товара.

    Args:
        product_id: ID товара

    Returns:
        Optional[float]: Последняя цена или None
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT price
                FROM price_history
                WHERE product_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (product_id,))

            row = cursor.fetchone()
            return row['price'] if row else None

    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении последней цены для товара {product_id}: {e}")
        return None


def get_price_history(product_id: int, days: int = 30) -> List[Dict]:
    """
    Получает историю цен товара за указанный период.

    Args:
        product_id: ID товара
        days: Количество дней для анализа (по умолчанию 30)

    Returns:
        List[Dict]: Список записей с полями price и timestamp
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # Вычисляем дату, с которой начинаем выборку
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            cursor.execute("""
                SELECT price, timestamp
                FROM price_history
                WHERE product_id = ? AND timestamp >= ?
                ORDER BY timestamp ASC
            """, (product_id, cutoff_date))

            history = [dict(row) for row in cursor.fetchall()]
            logger.debug(f"Получено записей для товара {product_id}: {len(history)}")
            return history

    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении истории цен для товара {product_id}: {e}")
        return []


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def check_price_threshold(product_id: int, current_price: float) -> Tuple[bool, float]:
    """
    Проверяет, достигла ли цена порогового значения.

    Args:
        product_id: ID товара
        current_price: Текущая цена

    Returns:
        Tuple[bool, float]: (достигла ли порога, пороговое значение)
    """
    product = get_product(product_id)
    if not product:
        return False, 0.0

    threshold = product['threshold_price']
    is_below = current_price <= threshold

    if is_below:
        logger.info(f"Товар {product_id}: цена {current_price} <= {threshold}")
    else:
        logger.debug(f"Товар {product_id}: цена {current_price} > {threshold}")

    return is_below, threshold


def get_products_below_threshold() -> List[Dict]:
    """
    Получает список товаров, у которых последняя цена ниже порога.

    Returns:
        List[Dict]: Список товаров с текущими ценами
    """
    result = []

    for product in get_all_products():
        last_price = get_last_price(product['id'])
        if last_price and last_price <= product['threshold_price']:
            result.append({
                'product': product,
                'current_price': last_price
            })

    logger.info(f"Найдено товаров ниже порога: {len(result)}")
    return result


def cleanup_old_records(days: int = 90) -> int:
    """
    Удаляет старые записи о ценах.

    Args:
        days: Удалять записи старше этого количества дней

    Returns:
        int: Количество удаленных записей
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            cursor.execute("""
                DELETE FROM price_history
                WHERE timestamp < ?
            """, (cutoff_date,))

            deleted = cursor.rowcount
            conn.commit()

            logger.info(f"Удалено {deleted} старых записей о ценах")
            return deleted

    except sqlite3.Error as e:
        logger.error(f"Ошибка при очистке старых записей: {e}")
        return 0


def get_database_stats() -> Dict:
    """
    Получает статистику по базе данных.

    Returns:
        Dict: Статистика БД
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # Количество товаров
            cursor.execute("SELECT COUNT(*) as count FROM products")
            products_count = cursor.fetchone()['count']

            # Количество записей о ценах
            cursor.execute("SELECT COUNT(*) as count FROM price_history")
            history_count = cursor.fetchone()['count']

            # Первая запись
            cursor.execute("SELECT MIN(timestamp) as first FROM price_history")
            first_record = cursor.fetchone()['first']

            # Последняя запись
            cursor.execute("SELECT MAX(timestamp) as last FROM price_history")
            last_record = cursor.fetchone()['last']

            # Размер файла
            db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0

            return {
                'products_count': products_count,
                'price_records_count': history_count,
                'first_record': first_record,
                'last_record': last_record,
                'database_size_mb': round(db_size / (1024 * 1024), 2)
            }

    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении статистики БД: {e}")
        return {}


# ========== ТЕСТИРОВАНИЕ ==========

if __name__ == "__main__":
    # Настройка логирования для теста
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ МОДУЛЯ DATABASE")
    print("=" * 60)

    # 1. Инициализация БД
    print("\n1️⃣ Инициализация базы данных...")
    if init_db():
        print("   ✅ База данных инициализирована")
    else:
        print("   ❌ Ошибка инициализации")
        exit(1)

    # 2. Добавление товаров
    print("\n2️⃣ Добавление тестовых товаров...")

    product1_id = add_product(
        url="http://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        name="A Light in the Attic",
        threshold=50.00
    )
    print(f"   ✅ Товар 1 добавлен с ID: {product1_id}")

    product2_id = add_product(
        url="http://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html",
        name="Tipping the Velvet",
        threshold=55.00
    )
    print(f"   ✅ Товар 2 добавлен с ID: {product2_id}")

    # 3. Сохранение цен
    print("\n3️⃣ Сохранение истории цен...")

    if save_price(product1_id, 51.77):
        print(f"   ✅ Цена сохранена для товара {product1_id}")
    if save_price(product1_id, 49.99):
        print(f"   ✅ Цена сохранена для товара {product1_id}")
    if save_price(product1_id, 48.50):
        print(f"   ✅ Цена сохранена для товара {product1_id}")

    if save_price(product2_id, 53.74):
        print(f"   ✅ Цена сохранена для товара {product2_id}")
    if save_price(product2_id, 54.20):
        print(f"   ✅ Цена сохранена для товара {product2_id}")

    # 4. Получение всех товаров
    print("\n4️⃣ Список всех товаров:")
    products = get_all_products()
    for product in products:
        print(f"   • [{product['id']}] {product['name']}")
        print(f"     URL: {product['url']}")
        print(f"     Порог: {product['threshold_price']}")

    # 5. Получение последней цены
    print("\n5️⃣ Последние цены:")
    for product in products:
        last_price = get_last_price(product['id'])
        print(f"   • {product['name']}: {last_price}")

    # 6. История цен
    print("\n6️⃣ История цен за 30 дней:")
    for product in products:
        history = get_price_history(product['id'], days=30)
        print(f"   • {product['name']}: {len(history)} записей")
        for record in history[-3:]:  # Показываем последние 3 записи
            print(f"     - {record['timestamp']}: {record['price']}")

    # 7. Проверка порогов
    print("\n7️⃣ Проверка пороговых значений:")
    for product in products:
        last_price = get_last_price(product['id'])
        if last_price:
            below, threshold = check_price_threshold(product['id'], last_price)
            status = "НИЖЕ ПОРОГА!" if below else "выше порога"
            print(f"   • {product['name']}: {last_price} / {threshold} - {status}")

    # 8. Товары ниже порога
    print("\n8️⃣ Товары ниже пороговой цены:")
    below = get_products_below_threshold()
    if below:
        for item in below:
            print(f"   • {item['product']['name']}: {item['current_price']}")
    else:
        print("   • Нет таких товаров")

    # 9. Статистика БД
    print("\n9️⃣ Статистика базы данных:")
    stats = get_database_stats()
    for key, value in stats.items():
        print(f"   • {key}: {value}")

    print("\n" + "=" * 60)
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 60)