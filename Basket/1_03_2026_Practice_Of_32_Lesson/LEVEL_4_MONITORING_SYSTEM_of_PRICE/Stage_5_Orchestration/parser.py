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

import requests
from bs4 import BeautifulSoup
import re
import time
import logging
import random
from urllib3.exceptions import InsecureRequestWarning

# Подавляем предупреждения об SSL
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


class PriceParser:
    """Класс для парсинга цен с учебных сайтов"""

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Создание сессии с настройками
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

        # Отключаем проверку SSL для учебных сайтов
        self.session.verify = config.verify_ssl

        # Специфичные парсеры для разных сайтов
        self.site_parsers = {
            'books.toscrape.com': self._parse_books_toscrape,
            'quotes.toscrape.com': self._parse_quotes_toscrape,
            'httpbin.org': self._parse_httpbin,
        }

    def get_price(self, url, selectors=None):
        """
        Получение данных с веб-страницы

        Args:
            url (str): URL товара
            selectors (dict): Селекторы для парсинга

        Returns:
            dict: Словарь с данными
        """
        try:
            # Определяем сайт по URL
            domain = self._get_domain(url)

            # Пробуем использовать специфичный парсер
            if domain in self.site_parsers:
                self.logger.info(f"🌐 Используется парсер для {domain}")
                return self.site_parsers[domain](url)

            # Универсальный парсер
            return self._parse_generic(url, selectors)

        except Exception as e:
            self.logger.error(f"❌ Ошибка парсинга {url}: {e}")

            # Возвращаем тестовые данные при ошибке
            if self.config.use_mock_on_error:
                return self._get_mock_data(url)
            return None

    def _get_domain(self, url):
        """Извлечение домена из URL"""
        match = re.search(r'https?://([^/]+)', url)
        return match.group(1) if match else ''

    def _parse_books_toscrape(self, url):
        """Парсер для books.toscrape.com"""
        self.logger.info(f"📚 Парсинг книги с books.toscrape.com")

        response = self.session.get(url, timeout=self.config.timeout)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        # Название книги
        title_elem = soup.find('h1')
        title = title_elem.text.strip() if title_elem else "Неизвестная книга"

        # Цена
        price_elem = soup.find('p', class_='price_color')
        price_text = price_elem.text.strip() if price_elem else "£0.00"
        price = self._clean_price(price_text)

        # Доступность
        avail_elem = soup.find('p', class_='instock availability')
        availability = avail_elem.text.strip() if avail_elem else "In stock"

        return {
            'name': title,
            'price': price,
            'currency': 'GBP',
            'availability': availability,
            'url': url,
            'price_found': price > 0,
            'is_mock': False
        }

    def _parse_quotes_toscrape(self, url):
        """Парсер для quotes.toscrape.com"""
        self.logger.info(f"💬 Парсинг цитат с quotes.toscrape.com")

        response = self.session.get(url, timeout=self.config.timeout)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Первая цитата на странице
        quote_elem = soup.find('span', class_='text')
        quote = quote_elem.text.strip() if quote_elem else "Нет цитат"

        # Автор
        author_elem = soup.find('small', class_='author')
        author = author_elem.text.strip() if author_elem else "Неизвестный автор"

        # Для этого сайта нет цен, генерируем тестовую
        price = random.uniform(10, 100)

        return {
            'name': f"Цитата: {author}",
            'price': price,
            'currency': 'RUB',
            'quote': quote,
            'author': author,
            'url': url,
            'price_found': True,
            'is_mock': False
        }

    def _parse_httpbin(self, url):
        """Парсер для httpbin.org"""
        self.logger.info(f"🌐 Тестирование HTTP сервера")

        response = self.session.get(url, timeout=self.config.timeout)
        data = response.json()

        # Тестовая цена на основе ответа
        price = random.uniform(500, 1500)

        return {
            'name': f"HTTP Test ({response.status_code})",
            'price': price,
            'currency': 'RUB',
            'headers': dict(response.headers),
            'url': url,
            'price_found': True,
            'is_mock': False
        }

    def _parse_generic(self, url, selectors=None):
        """Универсальный парсер"""
        self.logger.info(f"🔍 Используется универсальный парсер")

        response = self.session.get(url, timeout=self.config.timeout)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Поиск цены
        price = None
        if selectors and selectors.get('price_selector'):
            price_elem = soup.select_one(selectors['price_selector'])
            if price_elem:
                price = self._clean_price(price_elem.text)

        # Поиск названия
        name = None
        if selectors and selectors.get('name_selector'):
            name_elem = soup.select_one(selectors['name_selector'])
            if name_elem:
                name = name_elem.text.strip()

        if not price:
            # Пробуем найти цену по общим паттернам
            price = self._find_price_in_text(soup.get_text())

        if not name:
            title = soup.find('title')
            name = title.text.strip() if title else url

        return {
            'name': name,
            'price': price or 0.0,
            'currency': self._detect_currency(soup.get_text()),
            'url': url,
            'price_found': price is not None,
            'is_mock': False
        }

    def _get_mock_data(self, url):
        """Генерация тестовых данных"""
        self.logger.info(f"🔄 Генерация тестовых данных для {url}")

        domain = self._get_domain(url)

        mock_data = {
            'url': url,
            'name': f"Тестовый товар ({domain})",
            'price': round(random.uniform(100, 2000), 2),
            'currency': random.choice(['RUB', 'USD', 'EUR']),
            'price_found': True,
            'is_mock': True,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }

        # Специфичные тестовые данные для разных доменов
        if 'books' in domain:
            mock_data['name'] = f"📖 Тестовая книга #{random.randint(1, 100)}"
            mock_data['price'] = round(random.uniform(10, 50), 2)
            mock_data['currency'] = 'GBP'
        elif 'quotes' in domain:
            mock_data['name'] = f"💬 Тестовая цитата #{random.randint(1, 100)}"
            mock_data['price'] = round(random.uniform(5, 30), 2)

        return mock_data

    def _clean_price(self, price_text):
        """Очистка текста цены"""
        if not price_text:
            return 0.0

        # Удаляем все кроме цифр, точки и запятой
        cleaned = re.sub(r'[^\d.,]', '', price_text)
        cleaned = cleaned.replace(',', '.')

        # Удаляем лишние точки
        parts = cleaned.split('.')
        if len(parts) > 2:
            cleaned = parts[0] + '.' + ''.join(parts[1:])

        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def _find_price_in_text(self, text):
        """Поиск цены в тексте"""
        patterns = [
            r'£\s*(\d+\.?\d*)',
            r'\$\s*(\d+\.?\d*)',
            r'€\s*(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*[₽руб]',
            r'(\d+[.,]\d+)\s*[₽$€£]'
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return float(match.group(1).replace(',', '.'))

        return None

    def _detect_currency(self, text):
        """Определение валюты"""
        if '£' in text:
            return 'GBP'
        elif '$' in text:
            return 'USD'
        elif '€' in text:
            return 'EUR'
        elif '₽' in text or 'руб' in text.lower():
            return 'RUB'
        return 'RUB'