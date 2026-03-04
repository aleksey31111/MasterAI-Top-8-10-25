#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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

"""
Модуль для парсинга цен и названий товаров с различных источников.
Поддерживает HTML страницы и JSON API.
"""

import requests
from bs4 import BeautifulSoup
import logging
import re
import json
import time
from typing import Optional, Tuple, Dict, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/json,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}


class PriceParsingError(Exception):
    """Исключение при ошибках парсинга"""
    pass


class SiteScraper:
    """
    Класс для парсинга информации о товарах из разных источников.
    Поддерживает HTML и JSON форматы.
    """

    def __init__(self, config: dict = None):
        """
        Инициализация парсера.

        Args:
            config: Конфигурация с настройками
        """
        self.config = config or {}
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

        if 'user_agent' in self.config:
            self.session.headers['User-Agent'] = self.config['user_agent']

        self.timeout = self.config.get('timeout', DEFAULT_TIMEOUT)
        self.request_delay = self.config.get('request_delay', 1)
        self.last_request_time = 0

    def _wait_for_rate_limit(self):
        """Соблюдает задержку между запросами"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.request_delay and self.last_request_time > 0:
            sleep_time = self.request_delay - time_since_last
            logger.debug(f"Rate limit: ожидание {sleep_time:.2f} сек")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _make_request(self, url: str) -> requests.Response:
        """
        Выполняет HTTP-запрос с учётом rate limiting.

        Args:
            url: URL для запроса

        Returns:
            requests.Response: Ответ сервера

        Raises:
            PriceParsingError: При ошибках запроса
        """
        self._wait_for_rate_limit()

        try:
            logger.debug(f"Загрузка: {url}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка запроса: {e}")
            raise PriceParsingError(f"Ошибка запроса: {e}")

    def _parse_html(self, html: str, site_config: Dict[str, Any]) -> Tuple[Optional[float], Optional[str]]:
        """
        Парсит HTML страницу.

        Args:
            html: HTML контент
            site_config: Конфигурация сайта

        Returns:
            Tuple[float, str]: (цена, название)
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Извлекаем название
        name = None
        if site_config.get('name_selector'):
            name_elem = soup.select_one(site_config['name_selector'])
            if name_elem:
                name = name_elem.get_text(strip=True)

        # Если название не найдено, пробуем h1 или title
        if not name:
            h1 = soup.find('h1')
            if h1:
                name = h1.get_text(strip=True)
            else:
                title = soup.find('title')
                if title:
                    name = title.get_text(strip=True).split('|')[0].strip()

        # Извлекаем цену
        price = None
        if site_config.get('extract_as') == 'text':
            # Для httpbin просто возвращаем длину текста как "цену"
            price = len(soup.get_text()) / 100
            logger.debug(f"HTTP Bin: длина текста {price * 100}, цена {price}")

        elif site_config.get('price_selector'):
            price_elem = soup.select_one(site_config['price_selector'])
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                logger.debug(f"Текст с ценой: {price_text}")

                # Используем паттерн из конфига или стандартный
                pattern = site_config.get('price_pattern', r'[\d,]+\.?\d*')
                match = re.search(pattern, price_text)

                if match:
                    # Если есть группа захвата, используем её
                    price_str = match.group(1) if match.groups() else match.group(0)
                    # Убираем запятые и пробелы
                    price_str = price_str.replace(',', '').replace(' ', '')
                    try:
                        price = float(price_str)
                    except ValueError:
                        logger.warning(f"Не удалось преобразовать '{price_str}' в число")

        return price, name

    def _parse_json(self, json_data: dict, site_config: Dict[str, Any]) -> Tuple[Optional[float], Optional[str]]:
        """
        Парсит JSON ответ от API.

        Args:
            json_data: JSON данные
            site_config: Конфигурация сайта

        Returns:
            Tuple[float, str]: (цена, название)
        """
        price = None
        name = None

        # Извлекаем цену по JSON Path (упрощённо)
        if site_config.get('price_json_path'):
            keys = site_config['price_json_path'].split('.')
            value = json_data
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    value = None
                    break
            if value is not None:
                try:
                    price = float(value)
                except (ValueError, TypeError):
                    logger.warning(f"Не удалось преобразовать цену: {value}")

        # Извлекаем название
        if site_config.get('name_json_path'):
            keys = site_config['name_json_path'].split('.')
            value = json_data
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    value = None
                    break
            if value is not None:
                name = str(value)

        return price, name

    def get_product_info(self, url: str, site_config: Dict[str, Any]) -> Tuple[Optional[float], Optional[str]]:
        """
        Получает цену и название товара из различных источников.

        Args:
            url: URL товара или API endpoint
            site_config: Конфигурация сайта с параметрами парсинга

        Returns:
            Tuple[float, str]: (цена, название) или (None, None) при ошибке
        """
        try:
            response = self._make_request(url)
            content_type = response.headers.get('content-type', '').lower()

            price = None
            name = None

            # Определяем тип контента
            if site_config.get('type') == 'api' or 'application/json' in content_type:
                logger.debug("Парсинг JSON ответа")
                try:
                    json_data = response.json()
                    price, name = self._parse_json(json_data, site_config)
                except json.JSONDecodeError as e:
                    logger.error(f"Ошибка парсинга JSON: {e}")

            else:
                logger.debug("Парсинг HTML страницы")
                price, name = self._parse_html(response.text, site_config)

            # Для httpbin специальная обработка
            if 'httpbin.org' in url:
                logger.info(f"HTTP Bin test: получен текст длиной {len(response.text)} символов")

            # Ограничиваем длину названия
            if name and len(name) > 100:
                name = name[:97] + "..."

            logger.info(f"Результат: {url} -> цена={price}, название={name}")
            return price, name

        except PriceParsingError as e:
            logger.error(f"Ошибка парсинга: {e}")
            return None, None
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {e}")
            return None, None


# Функции для быстрого тестирования
def test_books_to_scrape():
    """Тестирует парсинг Books to Scrape"""
    scraper = SiteScraper()
    config = {
        'name_selector': 'h1',
        'price_selector': '.price_color',
        'price_pattern': r'£(\d+\.\d{2})',
        'type': 'html'
    }
    url = "http://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
    price, name = scraper.get_product_info(url, config)
    print(f"Books to Scrape: {name} - {price}£")
    return price, name


def test_fake_store_api():
    """Тестирует парсинг Fake Store API"""
    scraper = SiteScraper()
    config = {
        'type': 'api',
        'price_json_path': 'price',
        'name_json_path': 'title'
    }
    url = "https://fakestoreapi.com/products/1"
    price, name = scraper.get_product_info(url, config)
    print(f"Fake Store API: {name} - ${price}")
    return price, name


def test_httpbin():
    """Тестирует парсинг HTTP Bin"""
    scraper = SiteScraper()
    config = {
        'type': 'html',
        'extract_as': 'text',
        'name_selector': 'h1'
    }
    url = "https://httpbin.org/html"
    price, name = scraper.get_product_info(url, config)
    print(f"HTTP Bin: {name} - {price} (условная цена)")
    return price, name


if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)

    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ РАЗЛИЧНЫХ ИСТОЧНИКОВ ДАННЫХ")
    print("=" * 60)

    # Тест 1: Books to Scrape
    print("\n📚 Тест 1: Books to Scrape")
    test_books_to_scrape()

    # Тест 2: Fake Store API
    print("\n🌐 Тест 2: Fake Store API")
    test_fake_store_api()

    # Тест 3: HTTP Bin
    print("\n📄 Тест 3: HTTP Bin")
    test_httpbin()