#!/usr/bin/env python3
"""
Профессиональный сборщик цитат с сайта quotes.toscrape.com
Версия: 3.0.0 (Production-ready)
Автор: Студент-исследователь
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
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from tqdm import tqdm
import hashlib

# Попытка импорта YAML с fallback на JSON
try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class QuoteScraper:
    """
    Профессиональный парсер цитат с обработкой ошибок и множеством возможностей
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Инициализация парсера с загрузкой конфигурации
        """
        # Загружаем конфигурацию
        self.config = self.load_config(config_path)

        # Настройка логирования
        self.setup_logging()

        # Настройка HTTP сессии с повторными попытками
        self.setup_session()

        # Инициализация переменных для сбора данных
        self.all_quotes: List[Dict] = []
        self.quotes_hashes: Set[str] = set()  # Для проверки уникальности
        self.pages_data: List[Dict] = []  # Для хранения информации о страницах

        # Статистика
        self.stats = {
            'pages_visited': 0,
            'quotes_found': 0,
            'quotes_unique': 0,
            'quotes_duplicates': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }

        # Флаг для graceful shutdown
        self.running = True
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        self.logger.info("🚀 Парсер инициализирован")

    def load_config(self, config_path: Optional[str] = None) -> Dict:
        """
        Загрузка конфигурации из файла (YAML или JSON)
        """
        # Конфигурация по умолчанию
        default_config = {
            'scraper': {
                'name': 'QuoteScraper',
                'base_url': 'http://quotes.toscrape.com',
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'default_delay': 1,
                'max_retries': 3,
                'timeout': 10,
                'respect_robots': True,
                'max_pages': None  # None = все страницы
            },
            'selectors': {
                'quote': 'div.quote',
                'text': 'span.text',
                'author': 'small.author',
                'tags': 'a.tag',
                'next_page': 'li.next a'
            },
            'validation': {
                'min_text_length': 5,
                'max_text_length': 500,
                'required_fields': ['text', 'author']
            },
            'output': {
                'formats': ['json', 'csv', 'txt'],
                'encoding': 'utf-8',
                'pretty_print': True,
                'directory': 'output'
            },
            'logging': {
                'level': 'INFO',
                'file': 'logs/scraper.log',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            }
        }

        # Если указан путь к конфигурации, загружаем
        if config_path and Path(config_path).exists():
            try:
                if config_path.endswith(('.yaml', '.yml')) and YAML_AVAILABLE:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        user_config = yaml.safe_load(f)
                else:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        user_config = json.load(f)

                # Глубокое слияние конфигураций
                default_config = self._deep_merge(default_config, user_config)
                self.logger.info(f"✅ Конфигурация загружена из {config_path}")

            except Exception as e:
                print(f"⚠️ Ошибка загрузки конфигурации: {e}")
                print("🔄 Используется конфигурация по умолчанию")

        return default_config

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """
        Глубокое слияние двух словарей
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
        return base

    def setup_logging(self):
        """
        Настройка системы логирования
        """
        log_config = self.config['logging']

        # Создаем директорию для логов
        log_dir = Path(log_config['file']).parent
        log_dir.mkdir(exist_ok=True)

        # Настройка логирования
        logging.basicConfig(
            level=getattr(logging, log_config['level']),
            format=log_config['format'],
            handlers=[
                logging.FileHandler(log_config['file'], encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

        self.logger = logging.getLogger(self.config['scraper']['name'])

    def setup_session(self):
        """
        Настройка HTTP сессии с повторными попытками
        """
        self.session = requests.Session()

        # Настройка стратегии повторных попыток
        retry_strategy = Retry(
            total=self.config['scraper']['max_retries'],
            backoff_factor=0.5,  # Задержка: 0.5, 1, 2 секунды
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )

        # Создаем адаптер с нашей стратегией
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=20,
            pool_maxsize=20
        )

        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Устанавливаем заголовки
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
                # Простая проверка на запрет парсинга
                robots_content = response.text.lower()
                user_agent = self.config['scraper']['user_agent'].lower()

                # Ищем запреты для нашего user-agent
                if f"user-agent: {user_agent}" in robots_content and "disallow: /" in robots_content:
                    self.logger.warning("⚠️ robots.txt запрещает парсинг для нашего User-Agent")
                    return False

                # Проверяем общий запрет для всех
                if "user-agent: *" in robots_content and "disallow: /" in robots_content:
                    self.logger.warning("⚠️ robots.txt запрещает парсинг для всех пользователей")
                    return False

            self.logger.info("✅ robots.txt проверен, парсинг разрешён")
            return True

        except Exception as e:
            self.logger.warning(f"⚠️ Не удалось проверить robots.txt: {e}")
            return True  # Продолжаем, если не удалось проверить

    def safe_request(self, url: str) -> Optional[requests.Response]:
        """
        Безопасный запрос с обработкой ошибок
        """
        try:
            response = self.session.get(
                url,
                timeout=self.config['scraper']['timeout']
            )
            response.raise_for_status()
            return response

        except requests.exceptions.Timeout:
            self.logger.error(f"⏰ Таймаут при запросе к {url}")
            self.stats['errors'] += 1
            return None

        except requests.exceptions.ConnectionError:
            self.logger.error(f"🔌 Ошибка соединения с {url}")
            self.stats['errors'] += 1
            return None

        except requests.exceptions.HTTPError as e:
            self.logger.error(f"🌐 HTTP ошибка {e.response.status_code} для {url}")
            self.stats['errors'] += 1
            return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Ошибка запроса: {e}")
            self.stats['errors'] += 1
            return None

    def parse_quote(self, quote_element, page_num: int, page_url: str) -> Optional[Dict]:
        """
        Парсинг одной цитаты из HTML элемента
        """
        try:
            # Извлекаем текст цитаты
            text_elem = quote_element.select_one(self.config['selectors']['text'])
            if not text_elem:
                return None
            quote_text = text_elem.text.strip()

            # Извлекаем автора
            author_elem = quote_element.select_one(self.config['selectors']['author'])
            author = author_elem.text.strip() if author_elem else "Unknown"

            # Извлекаем теги
            tag_elems = quote_element.select(self.config['selectors']['tags'])
            tags = [tag.text.strip() for tag in tag_elems] if tag_elems else []

            # Создаем хеш для проверки уникальности
            quote_hash = hashlib.md5(f"{quote_text}|{author}".encode('utf-8')).hexdigest()

            # Проверка на уникальность
            if quote_hash in self.quotes_hashes:
                self.stats['quotes_duplicates'] += 1
                return None

            # Создаем объект цитаты
            quote_data = {
                'text': quote_text,
                'author': author,
                'tags': tags,
                'page': page_num,
                'url': page_url,
                'hash': quote_hash,
                'timestamp': datetime.now().isoformat()
            }

            # Валидация
            if self._validate_quote(quote_data):
                self.quotes_hashes.add(quote_hash)
                return quote_data
            else:
                self.logger.debug(f"❌ Цитата не прошла валидацию: {quote_text[:50]}...")
                return None

        except Exception as e:
            self.logger.error(f"Ошибка при парсинге цитаты: {e}")
            self.stats['errors'] += 1
            return None

    def _validate_quote(self, quote: Dict) -> bool:
        """
        Валидация данных цитаты
        """
        validation = self.config['validation']

        # Проверка обязательных полей
        for field in validation['required_fields']:
            if field not in quote or not quote[field]:
                return False

        # Проверка длины текста
        text_length = len(quote.get('text', ''))
        if text_length < validation['min_text_length'] or text_length > validation['max_text_length']:
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
            self.logger.debug(f"➡️ Найдена следующая страница: {next_url}")
            return next_url

        return None

    def scrape_page(self, url: str, page_num: int) -> Optional[BeautifulSoup]:
        """
        Парсинг одной страницы
        """
        self.logger.info(f"📄 Страница {page_num}: {url}")

        # Задержка между запросами (кроме первой страницы)
        if page_num > 1:
            time.sleep(self.config['scraper']['default_delay'])

        # Отправка запроса
        response = self.safe_request(url)
        if not response:
            return None

        # Парсинг HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Поиск всех цитат на странице
        quote_elements = soup.select(self.config['selectors']['quote'])
        self.logger.info(f"🔍 Найдено {len(quote_elements)} цитат на странице {page_num}")

        # Парсинг каждой цитаты
        page_quotes = []
        for quote_elem in quote_elements:
            quote = self.parse_quote(quote_elem, page_num, url)
            if quote:
                page_quotes.append(quote)
                self.stats['quotes_unique'] += 1

            self.stats['quotes_found'] += 1

        # Добавляем цитаты в общий список
        self.all_quotes.extend(page_quotes)
        self.stats['pages_visited'] += 1

        self.logger.info(f"✅ Собрано {len(page_quotes)} уникальных цитат со страницы {page_num}")

        return soup

    def scrape_all(self, start_url: str) -> List[Dict]:
        """
        Сбор всех цитат со всех страниц
        """
        self.stats['start_time'] = datetime.now()
        self.logger.info("=" * 60)
        self.logger.info(f"🚀 НАЧАЛО СБОРА ЦИТАТ")
        self.logger.info(f"📌 Стартовый URL: {start_url}")
        self.logger.info("=" * 60)

        # Проверка robots.txt
        if not self.check_robots_txt(start_url):
            self.logger.error("❌ Парсинг запрещён robots.txt")
            return []

        current_url = start_url
        page_num = 1
        max_pages = self.config['scraper']['max_pages']

        # Сбор всех страниц
        with tqdm(desc="Сбор страниц", unit="стр") as pbar:
            while current_url and self.running:
                # Проверка лимита страниц
                if max_pages and page_num > max_pages:
                    self.logger.info(f"🏁 Достигнут лимит страниц ({max_pages})")
                    break

                # Парсинг текущей страницы
                soup = self.scrape_page(current_url, page_num)
                if not soup:
                    break

                # Сохраняем информацию о странице
                self.pages_data.append({
                    'number': page_num,
                    'url': current_url,
                    'quotes_count': len(soup.select(self.config['selectors']['quote']))
                })

                pbar.update(1)
                pbar.set_postfix({
                    'страница': page_num,
                    'цитат': self.stats['quotes_unique']
                })

                # Поиск следующей страницы
                current_url = self.get_next_page_url(soup, current_url)
                page_num += 1

        self.stats['end_time'] = datetime.now()

        # Финальная статистика
        self._print_statistics()

        return self.all_quotes

    def _print_statistics(self):
        """
        Вывод подробной статистики
        """
        duration = self.stats['end_time'] - self.stats['start_time']
        duration_sec = duration.total_seconds()

        self.logger.info("=" * 60)
        self.logger.info("📊 СТАТИСТИКА СБОРА")
        self.logger.info("=" * 60)
        self.logger.info(f"📄 Страниц обработано: {self.stats['pages_visited']}")
        self.logger.info(f"🔍 Всего цитат найдено: {self.stats['quotes_found']}")
        self.logger.info(f"✨ Уникальных цитат: {self.stats['quotes_unique']}")
        self.logger.info(f"🔄 Дубликатов: {self.stats['quotes_duplicates']}")
        self.logger.info(f"❌ Ошибок: {self.stats['errors']}")
        self.logger.info(f"⏱️  Время выполнения: {duration_sec:.1f} сек")

        if self.stats['quotes_unique'] > 0 and duration_sec > 0:
            rate = self.stats['quotes_unique'] / duration_sec
            self.logger.info(f"⚡ Скорость: {rate:.1f} цитат/сек")

        # Статистика по авторам
        if self.all_quotes:
            from collections import Counter
            authors = [q['author'] for q in self.all_quotes]
            author_counts = Counter(authors)

            self.logger.info("\n🏆 Топ-5 авторов:")
            for author, count in author_counts.most_common(5):
                self.logger.info(f"   • {author}: {count} цитат")

            # Статистика по тегам
            all_tags = []
            for q in self.all_quotes:
                all_tags.extend(q['tags'])

            if all_tags:
                tag_counts = Counter(all_tags)
                self.logger.info("\n🏷️  Топ-5 тегов:")
                for tag, count in tag_counts.most_common(5):
                    self.logger.info(f"   • #{tag}: {count} раз")

        self.logger.info("=" * 60)

    def save_results(self, base_filename: str):
        """
        Сохранение результатов в различных форматах
        """
        if not self.all_quotes:
            self.logger.warning("⚠️ Нет данных для сохранения")
            return

        # Создаем директорию для выходных файлов
        output_dir = Path(self.config['output']['directory'])
        output_dir.mkdir(exist_ok=True)

        # Добавляем timestamp к имени файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_path = output_dir / f"{base_filename}_{timestamp}"

        formats = self.config['output']['formats']

        for fmt in formats:
            try:
                if fmt == 'json':
                    self._save_as_json(base_path.with_suffix('.json'))
                elif fmt == 'csv':
                    self._save_as_csv(base_path.with_suffix('.csv'))
                elif fmt == 'txt':
                    self._save_as_txt(base_path.with_suffix('.txt'))
                else:
                    self.logger.warning(f"⚠️ Неподдерживаемый формат: {fmt}")

            except Exception as e:
                self.logger.error(f"❌ Ошибка сохранения в {fmt}: {e}")

    def _save_as_json(self, filepath: Path):
        """
        Сохранение в JSON формате
        """
        output = {
            'metadata': {
                'total_quotes': len(self.all_quotes),
                'pages_visited': self.stats['pages_visited'],
                'start_time': self.stats['start_time'].isoformat() if self.stats['start_time'] else None,
                'end_time': self.stats['end_time'].isoformat() if self.stats['end_time'] else None,
                'config': self.config
            },
            'quotes': self.all_quotes
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            if self.config['output']['pretty_print']:
                json.dump(output, f, ensure_ascii=False, indent=2)
            else:
                json.dump(output, f, ensure_ascii=False)

        self.logger.info(f"💾 JSON сохранён: {filepath}")
        print(f"✅ JSON: {filepath}")

    def _save_as_csv(self, filepath: Path):
        """
        Сохранение в CSV формате
        """
        if not self.all_quotes:
            return

        # Подготовка данных для CSV
        csv_data = []
        for quote in self.all_quotes:
            csv_data.append({
                'text': quote['text'],
                'author': quote['author'],
                'tags': ', '.join(quote['tags']),
                'page': quote['page'],
                'url': quote['url']
            })

        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            fieldnames = ['text', 'author', 'tags', 'page', 'url']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_data)

        self.logger.info(f"💾 CSV сохранён: {filepath}")
        print(f"✅ CSV: {filepath}")

    def _save_as_txt(self, filepath: Path):
        """
        Сохранение в текстовом формате для чтения
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("СОБРАННЫЕ ЦИТАТЫ\n")
            f.write(f"Всего: {len(self.all_quotes)} цитат\n")
            f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")

            for i, quote in enumerate(self.all_quotes, 1):
                f.write(f"Цитата #{i} (стр. {quote['page']})\n")
                f.write(f"\"{quote['text']}\"\n")
                f.write(f"— {quote['author']}\n")
                if quote['tags']:
                    f.write(f"Теги: {', '.join(quote['tags'])}\n")
                f.write("-" * 60 + "\n\n")

        self.logger.info(f"💾 TXT сохранён: {filepath}")
        print(f"✅ TXT: {filepath}")

    def signal_handler(self, signum, frame):
        """
        Обработка сигналов прерывания (Ctrl+C)
        """
        self.logger.warning(f"⚠️ Получен сигнал {signum}, завершаем работу...")
        print("\n\n🛑 Получен сигнал прерывания. Завершаем работу...")
        self.running = False


def create_default_config():
    """
    Создание файла конфигурации по умолчанию
    """
    config = {
        'scraper': {
            'name': 'QuoteScraper',
            'base_url': 'http://quotes.toscrape.com',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'default_delay': 1,
            'max_retries': 3,
            'timeout': 10,
            'respect_robots': True,
            'max_pages': None
        },
        'selectors': {
            'quote': 'div.quote',
            'text': 'span.text',
            'author': 'small.author',
            'tags': 'a.tag',
            'next_page': 'li.next a'
        },
        'validation': {
            'min_text_length': 5,
            'max_text_length': 500,
            'required_fields': ['text', 'author']
        },
        'output': {
            'formats': ['json', 'csv', 'txt'],
            'encoding': 'utf-8',
            'pretty_print': True,
            'directory': 'output'
        },
        'logging': {
            'level': 'INFO',
            'file': 'logs/scraper.log',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        }
    }

    # Создаем JSON конфигурацию
    json_path = Path('config.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print(f"✅ Создан файл конфигурации: {json_path}")

    # Если YAML доступен, создаём YAML версию
    if YAML_AVAILABLE:
        yaml_path = Path('config.yaml')
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        print(f"✅ Создан файл конфигурации: {yaml_path}")

    # Создаем необходимые директории
    Path('logs').mkdir(exist_ok=True)
    Path('output').mkdir(exist_ok=True)
    print("✅ Созданы директории: logs/, output/")

    return json_path


def main():
    """
    Точка входа с парсингом аргументов командной строки
    """
    parser = argparse.ArgumentParser(
        description='Профессиональный сборщик цитат с сайта quotes.toscrape.com',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s --url http://quotes.toscrape.com
  %(prog)s --url http://quotes.toscrape.com --output my_quotes --delay 2
  %(prog)s --url http://quotes.toscrape.com --format json csv --config my_config.json
  %(prog)s --create-config
  %(prog)s --url http://quotes.toscrape.com --max-pages 5 --no-robots
        """
    )

    parser.add_argument(
        '--url',
        type=str,
        default='http://quotes.toscrape.com',
        help='URL для парсинга (по умолчанию: http://quotes.toscrape.com)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='quotes',
        help='Базовое имя выходного файла (по умолчанию: quotes)'
    )

    parser.add_argument(
        '--delay',
        type=float,
        help='Задержка между запросами в секундах'
    )

    parser.add_argument(
        '--format',
        type=str,
        nargs='+',
        choices=['json', 'csv', 'txt'],
        help='Форматы выходных файлов'
    )

    parser.add_argument(
        '--config',
        type=str,
        help='Путь к файлу конфигурации'
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

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Подробный вывод в консоль'
    )

    args = parser.parse_args()

    # Создание конфигурации по умолчанию
    if args.create_config:
        create_default_config()
        return

    # Создание парсера
    scraper = QuoteScraper(args.config)

    # Переопределение настроек из командной строки
    if args.delay is not None:
        scraper.config['scraper']['default_delay'] = args.delay

    if args.format is not None:
        scraper.config['output']['formats'] = args.format

    if args.no_robots:
        scraper.config['scraper']['respect_robots'] = False

    if args.max_pages is not None:
        scraper.config['scraper']['max_pages'] = args.max_pages

    if args.verbose:
        scraper.logger.setLevel(logging.DEBUG)

    # Запуск сбора цитат
    print("\n" + "=" * 60)
    print("🚀 ПРОФЕССИОНАЛЬНЫЙ СБОРЩИК ЦИТАТ")
    print("=" * 60 + "\n")

    quotes = scraper.scrape_all(args.url)

    # Сохранение результатов
    if quotes:
        scraper.save_results(args.output)
        print(f"\n✨ Готово! Собрано {len(quotes)} уникальных цитат")
        print(f"📁 Результаты сохранены в папке '{scraper.config['output']['directory']}/'")
    else:
        print("\n❌ Не удалось собрать цитаты")
        sys.exit(1)


if __name__ == "__main__":
    main()