'''
 Задача 1.2: Сбор данных в таблицу
Цель: Научиться запрашивать структурированные данные в формате CSV.
Промпт для ИИ:
```
Создай парсер для сбора информации о книгах с сайта http://books.toscrape.com/ (только первая страница).

Скрипт должен:
1. Загрузить главную страницу каталога
2. Для каждой книги извлечь:
   - Название (из тега <h3>/<a>)
   - Цену (из тега с классом "price_color")
   - Рейтинг (из класса "star-rating", например "star-rating Three" -> рейтинг 3)
   - Наличие (из тега с классом "instock availability")
3. Сохранить данные в CSV-файл с колонками: Название, Цена, Рейтинг, Наличие
4. Вывести в консоль статистику: сколько книг собрано, средняя цена
5. Добавить информативный вывод процесса в консоль

Код должен быть хорошо документирован и готов к запуску.
```
'''

import csv
import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Optional
import time

# --- Настройка логирования ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# --- Константы ---
TARGET_URL = "http://books.toscrape.com/"
OUTPUT_CSV_FILE = "books_catalog.csv"
REQUEST_TIMEOUT = 10
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# --- Маппинг рейтинга ---
RATING_MAP = {
    'One': 1,
    'Two': 2,
    'Three': 3,
    'Four': 4,
    'Five': 5
}

def fetch_page(url: str) -> Optional[BeautifulSoup]:
    """
    Загружает HTML-страницу и возвращает объект BeautifulSoup.

    Args:
        url: URL страницы для загрузки.

    Returns:
        Объект BeautifulSoup при успехе, None в случае ошибки.
    """
    headers = {'User-Agent': USER_AGENT}
    try:
        logger.info(f"🔄 Загружаем страницу: {url}")
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        response.encoding = 'utf-8' # Явно указываем кодировку
        logger.info("✅ Страница успешно загружена")
        return BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Ошибка при загрузке страницы: {e}")
        return None

def parse_books(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """
    Извлекает информацию о книгах из HTML-кода главной страницы каталога.

    Args:
        soup: Объект BeautifulSoup с HTML страницы.

    Returns:
        Список словарей, где каждый словарь содержит данные об одной книге.
    """
    books_data = []
    # Находим все элементы книг на странице (обычно они в <article class="product_pod">)
    book_articles = soup.find_all('article', class_='product_pod')
    logger.info(f"📦 Найдено книг на странице: {len(book_articles)}")

    if not book_articles:
        logger.warning("Не удалось найти карточки книг. Возможно, структура сайта изменилась.")
        return []

    for article in book_articles:
        try:
            # 1. Извлекаем название (находится в <h3><a> и содержит атрибут title)
            title_tag = article.find('h3').find('a')
            if not title_tag:
                logger.debug("Пропуск: не найдена ссылка с названием")
                continue
            title = title_tag.get('title', 'Нет названия').strip()

            # 2. Извлекаем цену
            price_tag = article.find('p', class_='price_color')
            price = price_tag.get_text(strip=True) if price_tag else 'Нет цены'

            # 3. Извлекаем рейтинг
            rating_tag = article.find('p', class_='star-rating')
            rating = 'Нет рейтинга'
            if rating_tag:
                # Класс рейтинга выглядит как "star-rating Three", берем второе слово
                rating_classes = rating_tag.get('class', [])
                if len(rating_classes) > 1:
                    rating_word = rating_classes[1]
                    rating = RATING_MAP.get(rating_word, f'Неизвестно ({rating_word})')

            # 4. Извлекаем наличие
            availability_tag = article.find('p', class_='instock availability')
            availability = availability_tag.get_text(strip=True) if availability_tag else 'Нет данных'

            book_info = {
                'Название': title,
                'Цена': price,
                'Рейтинг': rating,
                'Наличие': availability
            }
            books_data.append(book_info)
            logger.debug(f"  📖 Обработана: {title[:50]}...")

        except AttributeError as e:
            logger.warning(f"Ошибка парсинга элемента: {e}")
            continue

    logger.info(f"✅ Успешно извлечено данных: {len(books_data)} книг")
    return books_data

def save_to_csv(data: List[Dict], filename: str):
    """
    Сохраняет список книг в CSV-файл.

    Args:
        data: Список словарей с данными о книгах.
        filename: Имя выходного CSV-файла.
    """
    if not data:
        logger.warning("Нет данных для сохранения в CSV.")
        return

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Название', 'Цена', 'Рейтинг', 'Наличие']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            writer.writerows(data)

        logger.info(f"💾 Данные успешно сохранены в файл: {filename}")
    except IOError as e:
        logger.error(f"❌ Ошибка при записи в файл {filename}: {e}")

def calculate_statistics(data: List[Dict]) -> Dict:
    """
    Вычисляет статистику по собранным данным.

    Args:
        data: Список словарей с данными о книгах.

    Returns:
        Словарь со статистикой (количество, средняя цена).
    """
    if not data:
        return {'count': 0, 'avg_price': 0}

    total_books = len(data)
    prices = []
    for book in data:
        # Очищаем цену от символа '£' и преобразуем в число
        price_str = book['Цена'].replace('£', '').strip()
        try:
            prices.append(float(price_str))
        except ValueError:
            logger.debug(f"Не удалось преобразовать цену '{book['Цена']}' в число")

    avg_price = sum(prices) / len(prices) if prices else 0
    return {'count': total_books, 'avg_price': round(avg_price, 2)}

def display_statistics(stats: Dict):
    """Выводит статистику в консоль."""
    print("\n" + "="*40)
    print("📊 СТАТИСТИКА СБОРА")
    print("="*40)
    print(f"📚 Всего книг: {stats['count']}")
    print(f"💰 Средняя цена: £{stats['avg_price']}")
    print("="*40 + "\n")

def main():
    """Основная функция скрипта."""
    logger.info("🚀 Запуск парсера книг с http://books.toscrape.com/")

    # 1. Загрузка страницы
    soup = fetch_page(TARGET_URL)
    if not soup:
        logger.error("Не удалось загрузить страницу. Завершение работы.")
        return

    # 2. Парсинг данных
    books = parse_books(soup)

    # 3. Сохранение в CSV
    if books:
        save_to_csv(books, OUTPUT_CSV_FILE)
        # 4. Расчет и вывод статистики
        stats = calculate_statistics(books)
        display_statistics(stats)
    else:
        logger.warning("Не удалось извлечь данные о книгах.")

    logger.info("✅ Работа парсера завершена.")

if __name__ == "__main__":
    main()