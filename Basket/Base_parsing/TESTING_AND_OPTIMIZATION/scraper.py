#!/usr/bin/env python3
"""
Professional Web Scraper - Production-ready парсер для сбора данных с веб-сайтов
Author: Ваш покорный слуга
Version: 2.0.0
License: MIT
"""

import argparse
import requests
from bs4 import BeautifulSoup
import time
import json
import csv
import logging
import sys
import os
import signal
from datetime import datetime
from urllib.parse import urljoin, urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import yaml
import re
from typing import Dict, List, Optional, Any
from pathlib import Path


class ProfessionalScraper:
    """
    Профессиональный парсер с поддержкой конфигурации и множества форматов
    """

    def __init__(self, config_path: str = None):
        """
        Инициализация парсера с загрузкой конфигурации
        """
        # Загружаем конфигурацию
        self.config = self.load_config(config_path)

        # Настройка логирования
        self.setup_logging()

        # Настройка HTTP сессии
        self.setup_session()

        # Инициализация переменных
        self.collected_data = []
        self.stats = {
            'pages_visited': 0,
            'items_collected': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }

        # Флаг для graceful shutdown
        self.running = True
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def load_config(self, config_path: Optional[str] = None) -> Dict:
        """
        Загрузка конфигурации из YAML файла
        """
        default_config = {
            'scraper': {
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'default_delay': 1,
                'max_retries': 3,
                'timeout': 10,
                'respect_robots': True
            },
            'output': {
                'formats': ['json', 'csv'],
                'encoding': 'utf-8',
                'pretty_print': True
            },
            'selectors': {
                'quotes': 'div.quote',
                'text': 'span.text',
                'author': 'small.author',
                'tags': 'a.tag',
                'next_page': 'li.next a'
            },
            'validation': {
                'min_text_length': 5,
                'max_text_length': 500,
                'required_fields': ['text', 'author']
            }
        }

        if config_path and Path(config_path).exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f)
                # Глубокое слияние словарей
                default_config = self.deep_merge(default_config, user_config)
                self.logger.info(f"✅ Конфигурация загружена из {config_path}")
        else:
            if config_path:
                self.logger.warning(
                    f"⚠️ Файл конфигурации {config_path} не найден, используются настройки по умолчанию")

        return default_config

    def deep_merge(self, base: Dict, override: Dict) -> Dict:
        """
        Глубокое слияние словарей
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self.deep_merge(base[key], value)
            else:
                base[key] = value
        return base

    def setup_logging(self):
        """
        Настройка логирования с ротацией файлов
        """
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)

        log_filename = log_dir / f"scraper_{datetime.now().strftime('%Y%m%d')}.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_session(self):
        """
        Настройка HTTP сессии с повторными попытками
        """
        self.session = requests.Session()

        # Настройка повторных попыток
        retry_strategy = Retry(
            total=self.config['scraper']['max_retries'],
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )

        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=20,
            pool_maxsize=20
        )

        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Установка заголовков
        self.session.headers.update({
            'User-Agent': self.config['scraper']['user_agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })

    def check_robots_txt(self, base_url: str) -> bool:
        """
        Проверка robots.txt перед началом парсинга
        """
        if not self.config['scraper']['respect_robots']:
            return True

        parsed_url = urlparse(base_url)
        robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"

        try:
            response = self.session.get(robots_url, timeout=5)
            if response.status_code == 200:
                # Простая проверка: ищем "Disallow: /" для нашего user-agent
                robots_content = response.text
                if 'Disallow: /' in robots_content and f"User-agent: {self.config['scraper']['user_agent']}" in robots_content:
                    self.logger.warning("⚠️ robots.txt запрещает парсинг для нашего User-Agent")
                    return False
            self.logger.info("✅ robots.txt проверен, парсинг разрешён")
            return True
        except:
            self.logger.warning("⚠️ Не удалось проверить robots.txt, продолжаем...")
            return True

    def parse_page(self, url: str, soup: BeautifulSoup) -> List[Dict]:
        """
        Универсальный парсер страницы с поддержкой разных селекторов
        """
        items = []
        selectors = self.config['selectors']

        # Находим все элементы с данными
        elements = soup.select(selectors['quotes'])

        for element in elements:
            try:
                item = {}

                # Извлекаем текст
                text_elem = element.select_one(selectors['text'])
                if text_elem:
                    item['text'] = text_elem.text.strip()

                # Извлекаем автора
                author_elem = element.select_one(selectors['author'])
                if author_elem:
                    item['author'] = author_elem.text.strip()

                # Извлекаем теги
                tag_elems = element.select(selectors['tags'])
                if tag_elems:
                    item['tags'] = [tag.text.strip() for tag in tag_elems]

                # Добавляем метаданные
                item['url'] = url
                item['timestamp'] = datetime.now().isoformat()

                # Валидация
                if self.validate_item(item):
                    items.append(item)

            except Exception as e:
                self.logger.error(f"Ошибка при парсинге элемента: {e}")
                self.stats['errors'] += 1

        return items

    def validate_item(self, item: Dict) -> bool:
        """
        Валидация собранных данных
        """
        validation = self.config['validation']

        # Проверка обязательных полей
        for field in validation['required_fields']:
            if field not in item or not item[field]:
                self.logger.debug(f"Пропущен элемент: отсутствует поле {field}")
                return False

        # Проверка длины текста
        text_length = len(item.get('text', ''))
        if text_length < validation['min_text_length'] or text_length > validation['max_text_length']:
            self.logger.debug(f"Пропущен элемент: некорректная длина текста ({text_length})")
            return False

        return True

    def get_next_page_url(self, soup: BeautifulSoup, current_url: str) -> Optional[str]:
        """
        Поиск URL следующей страницы
        """
        next_selector = self.config['selectors']['next_page']
        next_elem = soup.select_one(next_selector)

        if next_elem and next_elem.get('href'):
            next_url = urljoin(current_url, next_elem['href'])
            return next_url

        return None

    def scrape(self, start_url: str, delay: float = None) -> List[Dict]:
        """
        Основной метод сбора данных
        """
        if delay is None:
            delay = self.config['scraper']['default_delay']

        self.stats['start_time'] = datetime.now()
        self.logger.info(f"🚀 Начинаем парсинг: {start_url}")

        # Проверка robots.txt
        if not self.check_robots_txt(start_url):
            self.logger.error("❌ Парсинг запрещён robots.txt")
            return []

        current_url = start_url
        page_num = 1

        try:
            while current_url and self.running:
                self.logger.info(f"📄 Страница {page_num}: {current_url}")

                try:
                    # Задержка между запросами
                    if page_num > 1:
                        time.sleep(delay)

                    # Отправка запроса
                    response = self.session.get(
                        current_url,
                        timeout=self.config['scraper']['timeout']
                    )
                    response.raise_for_status()

                    # Парсинг страницы
                    soup = BeautifulSoup(response.text, 'html.parser')

                    # Сбор данных
                    page_data = self.parse_page(current_url, soup)
                    self.collected_data.extend(page_data)

                    # Обновление статистики
                    self.stats['pages_visited'] += 1
                    self.stats['items_collected'] = len(self.collected_data)

                    self.logger.info(f"✅ Найдено {len(page_data)} элементов на странице {page_num}")

                    # Поиск следующей страницы
                    current_url = self.get_next_page_url(soup, current_url)
                    page_num += 1

                except requests.exceptions.RequestException as e:
                    self.logger.error(f"❌ Ошибка запроса: {e}")
                    self.stats['errors'] += 1
                    break

        except KeyboardInterrupt:
            self.logger.info("🛑 Парсинг прерван пользователем")
        finally:
            self.stats['end_time'] = datetime.now()
            self.print_statistics()

        return self.collected_data

    def save_results(self, filename: str, formats: List[str] = None):
        """
        Сохранение результатов в разных форматах
        """
        if formats is None:
            formats = self.config['output']['formats']

        if not self.collected_data:
            self.logger.warning("⚠️ Нет данных для сохранения")
            return

        base_name = Path(filename).stem
        output_dir = Path('output')
        output_dir.mkdir(exist_ok=True)

        for fmt in formats:
            try:
                if fmt == 'json':
                    self.save_as_json(output_dir / f"{base_name}.json")
                elif fmt == 'csv':
                    self.save_as_csv(output_dir / f"{base_name}.csv")
                elif fmt == 'txt':
                    self.save_as_txt(output_dir / f"{base_name}.txt")
                else:
                    self.logger.warning(f"⚠️ Неподдерживаемый формат: {fmt}")
            except Exception as e:
                self.logger.error(f"❌ Ошибка сохранения в {fmt}: {e}")

    def save_as_json(self, filepath: Path):
        """
        Сохранение в JSON
        """
        output = {
            'metadata': {
                'total_items': len(self.collected_data),
                'pages_visited': self.stats['pages_visited'],
                'start_time': self.stats['start_time'].isoformat() if self.stats['start_time'] else None,
                'end_time': self.stats['end_time'].isoformat() if self.stats['end_time'] else None,
                'config': self.config
            },
            'data': self.collected_data
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            if self.config['output']['pretty_print']:
                json.dump(output, f, ensure_ascii=False, indent=2)
            else:
                json.dump(output, f, ensure_ascii=False)

        self.logger.info(f"💾 JSON сохранён: {filepath}")

    def save_as_csv(self, filepath: Path):
        """
        Сохранение в CSV
        """
        if not self.collected_data:
            return

        # Определяем все возможные поля
        fieldnames = set()
        for item in self.collected_data:
            fieldnames.update(item.keys())

        # Преобразуем теги в строку
        for item in self.collected_data:
            if 'tags' in item and isinstance(item['tags'], list):
                item['tags'] = ', '.join(item['tags'])

        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=sorted(fieldnames))
            writer.writeheader()
            writer.writerows(self.collected_data)

        self.logger.info(f"💾 CSV сохранён: {filepath}")

    def save_as_txt(self, filepath: Path):
        """
        Сохранение в читаемый текстовый формат
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"РЕЗУЛЬТАТЫ ПАРСИНГА\n")
            f.write(f"Собрано: {len(self.collected_data)} элементов\n")
            f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")

            for i, item in enumerate(self.collected_data, 1):
                f.write(f"Элемент #{i}\n")
                for key, value in item.items():
                    if key not in ['url', 'timestamp']:  # Пропускаем метаданные
                        f.write(f"{key.capitalize()}: {value}\n")
                f.write("-" * 40 + "\n")

        self.logger.info(f"💾 TXT сохранён: {filepath}")

    def print_statistics(self):
        """
        Вывод статистики
        """
        duration = None
        if self.stats['start_time'] and self.stats['end_time']:
            duration = self.stats['end_time'] - self.stats['start_time']

        self.logger.info("=" * 60)
        self.logger.info("📊 СТАТИСТИКА")
        self.logger.info("=" * 60)
        self.logger.info(f"📄 Страниц обработано: {self.stats['pages_visited']}")
        self.logger.info(f"💬 Элементов собрано: {self.stats['items_collected']}")
        self.logger.info(f"❌ Ошибок: {self.stats['errors']}")
        if duration:
            self.logger.info(f"⏱️  Время: {duration.total_seconds():.1f} сек")
            if self.stats['items_collected'] > 0:
                rate = self.stats['items_collected'] / duration.total_seconds()
                self.logger.info(f"⚡ Скорость: {rate:.1f} эл/сек")
        self.logger.info("=" * 60)

    def signal_handler(self, signum, frame):
        """
        Обработка сигналов завершения
        """
        self.logger.warning(f"⚠️ Получен сигнал {signum}, завершаем работу...")
        self.running = False


def create_default_config():
    """
    Создание файла конфигурации по умолчанию
    """
    config = {
        'scraper': {
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'default_delay': 2,
            'max_retries': 3,
            'timeout': 10,
            'respect_robots': True
        },
        'output': {
            'formats': ['json', 'csv', 'txt'],
            'encoding': 'utf-8',
            'pretty_print': True
        },
        'selectors': {
            'quotes': 'div.quote',
            'text': 'span.text',
            'author': 'small.author',
            'tags': 'a.tag',
            'next_page': 'li.next a'
        },
        'validation': {
            'min_text_length': 5,
            'max_text_length': 500,
            'required_fields': ['text', 'author']
        }
    }

    config_path = Path('config.yaml')
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    print(f"✅ Создан файл конфигурации: {config_path}")
    return config_path


def main():
    """
    Точка входа с парсингом аргументов командной строки
    """
    parser = argparse.ArgumentParser(
        description='Professional Web Scraper - сбор данных с веб-сайтов',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s --url http://quotes.toscrape.com --output quotes --delay 2
  %(prog)s --url http://example.com --output data --format json csv --config my_config.yaml
  %(prog)s --create-config
        """
    )

    parser.add_argument(
        '--url',
        type=str,
        help='URL для парсинга'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='results',
        help='Имя выходного файла (без расширения)'
    )

    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Задержка между запросами в секундах'
    )

    parser.add_argument(
        '--format',
        type=str,
        nargs='+',
        choices=['json', 'csv', 'txt'],
        default=['json', 'csv'],
        help='Форматы выходных файлов'
    )

    parser.add_argument(
        '--config',
        type=str,
        help='Путь к файлу конфигурации YAML'
    )

    parser.add_argument(
        '--create-config',
        action='store_true',
        help='Создать файл конфигурации по умолчанию и выйти'
    )

    parser.add_argument(
        '--no-robots',
        action='store_true',
        help='Игнорировать robots.txt'
    )

    parser.add_argument(
        '--max-pages',
        type=int,
        help='Максимальное количество страниц для парсинга'
    )

    args = parser.parse_args()

    # Создание конфигурации
    if args.create_config:
        create_default_config()
        return

    # Проверка обязательных аргументов
    if not args.url:
        parser.error("Не указан URL. Используйте --url для указания целевого сайта")

    # Создание парсера
    scraper = ProfessionalScraper(args.config)

    # Переопределение настроек из командной строки
    if args.no_robots:
        scraper.config['scraper']['respect_robots'] = False

    # Запуск парсинга
    data = scraper.scrape(args.url, args.delay)

    # Сохранение результатов
    if data:
        scraper.save_results(args.output, args.format)
        print(f"\n✨ Готово! Данные сохранены в папке 'output/'")
    else:
        print("\n❌ Не удалось собрать данные")
        sys.exit(1)


if __name__ == "__main__":
    main()