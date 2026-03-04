'''
Задача 2.1: Сбор всех книг с пагинацией
Цель: Научиться описывать логику перехода между страницами.

Промпт для ИИ:
```
Усовершенствуй предыдущий парсер книг. Теперь нужно собрать ВСЕ книги со ВСЕХ страниц каталога http://books.toscrape.com/catalogue/page-1.html.

Особенности:
1. Начальная страница: http://books.toscrape.com/catalogue/page-1.html
2. На каждой странице есть ссылка "next" (если страница не последняя)
3. Нужно обходить страницы, пока не закончится пагинация
4. Добавить задержку в 1 секунду между запросами (для вежливости)
5. Сохранить все книги в один CSV-файл
6. Добавить прогресс-бар с помощью библиотеки tqdm
7. В конце вывести общую статистику: количество страниц, общее количество книг, среднюю цену

Важно: обработать случай, когда на последней странице нет кнопки "next"
```
'''
import csv
import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Optional, Tuple
import time
from tqdm import tqdm

# --- Настройка логирования ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# --- Константы ---
BASE_URL = "http://books.toscrape.com/catalogue/"
FIRST_PAGE_URL = f"{BASE_URL}page-1.html"
OUTPUT_CSV_FILE = "all_books_catalog.csv"
REQUEST_TIMEOUT = 10
REQUEST_DELAY = 1  # Задержка между запросами (секунд)
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# --- Маппинг рейтинга ---
RATING_MAP = {
    'One': 1,
    'Two': 2,
    'Three': 3,
    'Four': 4,
    'Five': 5
}

class BookScraper:
    """Класс для сбора информации о книгах с поддержкой пагинации."""

    def __init__(self, base_url: str, first_page_url: str):
        self.base_url = base_url
        self.current_url = first_page_url
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        self.books_data: List[Dict] = []
        self.page_count = 0

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """
        Загружает HTML-страницу и возвращает объект BeautifulSoup.

        Args:
            url: URL страницы для загрузки.

        Returns:
            Объект BeautifulSoup при успехе, None в случае ошибки.
        """
        try:
            logger.debug(f"Загрузка: {url}")
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return BeautifulSoup(response.text, 'html.parser')
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при загрузке {url}: {e}")
            return None

    def parse_books_from_page(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Извлекает информацию о книгах из HTML-кода одной страницы каталога.

        Args:
            soup: Объект BeautifulSoup с HTML страницы.

        Returns:
            Список словарей с данными о книгах на странице.
        """
        books_on_page = []
        book_articles = soup.find_all('article', class_='product_pod')

        if not book_articles:
            logger.warning("Не найдены карточки книг на странице.")
            return []

        for article in book_articles:
            try:
                # 1. Название
                title_tag = article.find('h3').find('a')
                title = title_tag.get('title', 'Нет названия').strip() if title_tag else 'Нет названия'

                # 2. Цена
                price_tag = article.find('p', class_='price_color')
                price = price_tag.get_text(strip=True) if price_tag else 'Нет цены'

                # 3. Рейтинг
                rating_tag = article.find('p', class_='star-rating')
                rating = 'Нет рейтинга'
                if rating_tag:
                    rating_classes = rating_tag.get('class', [])
                    if len(rating_classes) > 1:
                        rating_word = rating_classes[1]
                        rating = RATING_MAP.get(rating_word, f'Неизвестно ({rating_word})')

                # 4. Наличие
                availability_tag = article.find('p', class_='instock availability')
                availability = availability_tag.get_text(strip=True) if availability_tag else 'Нет данных'

                books_on_page.append({
                    'Название': title,
                    'Цена': price,
                    'Рейтинг': rating,
                    'Наличие': availability
                })

            except AttributeError as e:
                logger.warning(f"Ошибка парсинга элемента: {e}")
                continue

        return books_on_page

    def get_next_page_url(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Находит URL следующей страницы по ссылке "next".

        Args:
            soup: Объект BeautifulSoup текущей страницы.

        Returns:
            URL следующей страницы или None, если это последняя страница.
        """
        next_button = soup.find('li', class_='next')
        if next_button and next_button.find('a'):
            relative_link = next_button.find('a')['href']
            # Формируем полный URL
            if relative_link.startswith('page-'):
                return f"{self.base_url}{relative_link}"
            else:
                return requests.compat.urljoin(self.current_url, relative_link)
        return None

    def scrape_all_pages(self) -> List[Dict]:
        """
        Основной метод для обхода всех страниц каталога и сбора данных.
        Использует прогресс-бар tqdm для отображения процесса.
        """
        logger.info("🚀 Начинаем сбор данных со всех страниц каталога...")

        # Сначала нужно узнать общее количество страниц для прогресс-бара
        # Это можно сделать, загрузив первую страницу и найдя номер последней
        # Но проще использовать tqdm с неизвестным общим числом, обновляя вручную

        # Создаем прогресс-бар без общего количества (оно будет уточняться)
        pbar = tqdm(desc="Обработка страниц", unit="стр")

        while self.current_url:
            self.page_count += 1
            pbar.set_description(f"Стр. {self.page_count}")

            # Загружаем страницу
            soup = self.fetch_page(self.current_url)
            if not soup:
                logger.error(f"Не удалось загрузить страницу {self.current_url}. Прерывание.")
                break

            # Парсим книги на странице
            books = self.parse_books_from_page(soup)
            self.books_data.extend(books)

            # Логируем результат для страницы
            logger.info(f"📄 Страница {self.page_count}: найдено {len(books)} книг")

            # Обновляем прогресс-бар
            pbar.update(1)
            pbar.set_postfix({"книг": len(self.books_data)})

            # Ищем следующую страницу
            next_url = self.get_next_page_url(soup)

            if next_url:
                self.current_url = next_url
                # Вежливая задержка перед следующим запросом
                time.sleep(REQUEST_DELAY)
            else:
                logger.info("🏁 Достигнута последняя страница.")
                self.current_url = None

        pbar.close()
        logger.info(f"✅ Сбор завершен. Обработано страниц: {self.page_count}")
        return self.books_data

    def save_to_csv(self, filename: str):
        """Сохраняет все собранные данные в CSV-файл."""
        if not self.books_data:
            logger.warning("Нет данных для сохранения.")
            return

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['Название', 'Цена', 'Рейтинг', 'Наличие']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.books_data)
            logger.info(f"💾 Данные сохранены в файл: {filename}")
        except IOError as e:
            logger.error(f"❌ Ошибка при записи в файл {filename}: {e}")

    def calculate_statistics(self) -> Dict:
        """Вычисляет общую статистику по всем собранным книгам."""
        if not self.books_data:
            return {'total_pages': 0, 'total_books': 0, 'avg_price': 0}

        total_books = len(self.books_data)
        prices = []

        for book in self.books_data:
            price_str = book['Цена'].replace('£', '').replace('Â', '').strip()
            try:
                prices.append(float(price_str))
            except ValueError:
                logger.debug(f"Не удалось преобразовать цену: {book['Цена']}")

        avg_price = sum(prices) / len(prices) if prices else 0

        return {
            'total_pages': self.page_count,
            'total_books': total_books,
            'avg_price': round(avg_price, 2)
        }

    def display_statistics(self, stats: Dict):
        """Выводит итоговую статистику в консоль."""
        print("\n" + "="*50)
        print("📊 ИТОГОВАЯ СТАТИСТИКА СБОРА")
        print("="*50)
        print(f"📄 Всего обработано страниц: {stats['total_pages']}")
        print(f"📚 Всего собрано книг: {stats['total_books']}")
        print(f"💰 Средняя цена книги: £{stats['avg_price']}")
        print("="*50 + "\n")


def main():
    """Основная функция для запуска парсера."""
    scraper = BookScraper(BASE_URL, FIRST_PAGE_URL)

    try:
        # Запускаем сбор данных
        all_books = scraper.scrape_all_pages()

        # Сохраняем в CSV
        if all_books:
            scraper.save_to_csv(OUTPUT_CSV_FILE)

            # Выводим статистику
            stats = scraper.calculate_statistics()
            scraper.display_statistics(stats)
        else:
            logger.warning("Не удалось собрать данные о книгах.")

    except KeyboardInterrupt:
        logger.info("🛑 Получен сигнал прерывания. Завершение работы...")
        # Сохраняем то, что уже собрали
        if scraper.books_data:
            scraper.save_to_csv("partial_" + OUTPUT_CSV_FILE)
            logger.info(f"💾 Частичные данные сохранены в partial_{OUTPUT_CSV_FILE}")
    except Exception as e:
        logger.error(f"❌ Непредвиденная ошибка: {e}")


if __name__ == "__main__":
    main()