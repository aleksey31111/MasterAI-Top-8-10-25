#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
 УРОВЕНЬ 5: ОТЛАДКА И УЛУЧШЕНИЕ КОДА

 Задача 5.1: Оптимизация медленного парсера
Цель: Научиться просить ИИ проанализировать и улучшить существующий код.

Промпт для ИИ:
```
У меня есть парсер, который работает очень медленно. Вот код:

[
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для парсинга цен и названий товаров с веб-страниц.
Исправленная версия с ТОЛЬКО рабочими сайтами.
"""

import requests
from bs4 import BeautifulSoup
import logging
import re
from typing import Optional, Tuple, List
from urllib.parse import urlparse
import time

# Настройка логирования
logger = logging.getLogger(__name__)

# Константы
DEFAULT_TIMEOUT = 10
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


class PriceParsingError(Exception):
    """Исключение при ошибках парсинга цен"""
    pass


class SiteScraper:
    """
    Класс для парсинга информации о товарах с веб-страниц.
    Поддерживает только проверенные рабочие сайты.
    """

    # Только ГАРАНТИРОВАННО РАБОЧИЕ сайты
    WORKING_SITES = {
        'books.toscrape.com': {
            'name': 'Books to Scrape',
            'base_url': 'http://books.toscrape.com/',
            'product_pattern': '/catalogue/',
            'selectors': {
                'price': '.price_color',
                'name': 'h1',
            },
            'price_pattern': r'£(\d+\.\d{2})',
            'currency': '£'
        }
    }

    def __init__(self, config: dict = None):
        """Инициализация парсера"""
        self.config = config or {}
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.last_request_time = 0
        self.request_delay = self.config.get('request_delay', 1)

    def _wait_if_needed(self):
        """Соблюдение задержки между запросами"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.request_delay:
            time.sleep(self.request_delay - time_since_last)
        self.last_request_time = time.time()

    def _get_soup(self, url: str) -> Optional[BeautifulSoup]:
        """Получает HTML страницы с обработкой ошибок"""
        self._wait_if_needed()

        try:
            logger.debug(f"Загрузка: {url}")
            response = self.session.get(
                url,
                timeout=self.config.get('timeout', DEFAULT_TIMEOUT),
                allow_redirects=True
            )
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')

        except requests.exceptions.Timeout:
            logger.error(f"Таймаут: {url}")
        except requests.exceptions.ConnectionError:
            logger.error(f"Ошибка соединения: {url}")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP {e.response.status_code}: {url}")
        except Exception as e:
            logger.error(f"Ошибка: {e}")

        return None

    def is_site_supported(self, url: str) -> Tuple[bool, str]:
        """
        Проверяет, поддерживается ли сайт.

        Returns:
            Tuple[bool, str]: (поддерживается ли, название сайта или причина отказа)
        """
        domain = urlparse(url).netloc.replace('www.', '')

        for supported_domain, site_info in self.WORKING_SITES.items():
            if supported_domain in domain:
                # Проверяем, что это страница товара
                if site_info.get('product_pattern') in url:
                    return True, site_info['name']
                else:
                    return False, f"Это не страница товара для {site_info['name']}"

        return False, f"Сайт {domain} не поддерживается"

    def extract_price(self, text: str, pattern: str) -> Optional[float]:
        """Извлекает цену из текста"""
        try:
            match = re.search(pattern, text)
            if match:
                price_str = match.group(1) if match.groups() else match.group(0)
                price_str = price_str.replace(',', '')
                return float(price_str)
        except (ValueError, AttributeError) as e:
            logger.error(f"Ошибка преобразования цены: {e}")
        return None

    def get_price(self, url: str) -> Optional[float]:
        """Извлекает цену товара"""
        # Сначала проверяем, поддерживается ли сайт
        supported, site_name = self.is_site_supported(url)
        if not supported:
            logger.warning(f"⛔ {site_name}")
            return None

        logger.info(f"Получение цены: {url}")

        soup = self._get_soup(url)
        if not soup:
            return None

        # Получаем настройки для сайта
        domain = urlparse(url).netloc.replace('www.', '')
        site_config = None
        for d, config in self.WORKING_SITES.items():
            if d in domain:
                site_config = config
                break

        if not site_config:
            return None

        # Ищем цену
        price_element = soup.select_one(site_config['selectors']['price'])
        if not price_element:
            logger.warning(f"Цена не найдена")
            return None

        price_text = price_element.get_text(strip=True)
        price = self.extract_price(price_text, site_config['price_pattern'])

        if price is not None:
            logger.info(f"✅ Цена: {price} {site_config['currency']}")
            return price
        else:
            logger.warning(f"Не удалось извлечь цену из: {price_text}")
            return None

    def get_product_name(self, url: str) -> Optional[str]:
        """Извлекает название товара"""
        # Сначала проверяем, поддерживается ли сайт
        supported, site_name = self.is_site_supported(url)
        if not supported:
            logger.warning(f"⛔ {site_name}")
            return None

        logger.info(f"Получение названия: {url}")

        soup = self._get_soup(url)
        if not soup:
            return None

        # Получаем настройки для сайта
        domain = urlparse(url).netloc.replace('www.', '')
        site_config = None
        for d, config in self.WORKING_SITES.items():
            if d in domain:
                site_config = config
                break

        if not site_config:
            return None

        # Ищем название
        name_element = soup.select_one(site_config['selectors']['name'])
        if not name_element:
            logger.warning(f"Название не найдено")
            return None

        name = name_element.get_text(strip=True)
        logger.info(f"✅ Название: {name[:50]}...")
        return name

    def get_product_info(self, url: str) -> Tuple[Optional[float], Optional[str]]:
        """Получает и цену, и название за один запрос"""
        supported, site_name = self.is_site_supported(url)
        if not supported:
            logger.warning(f"⛔ {site_name}")
            return None, None

        soup = self._get_soup(url)
        if not soup:
            return None, None

        # Получаем настройки для сайта
        domain = urlparse(url).netloc.replace('www.', '')
        site_config = None
        for d, config in self.WORKING_SITES.items():
            if d in domain:
                site_config = config
                break

        if not site_config:
            return None, None

        # Извлекаем название
        name = None
        name_element = soup.select_one(site_config['selectors']['name'])
        if name_element:
            name = name_element.get_text(strip=True)

        # Извлекаем цену
        price = None
        price_element = soup.select_one(site_config['selectors']['price'])
        if price_element:
            price_text = price_element.get_text(strip=True)
            price = self.extract_price(price_text, site_config['price_pattern'])

        if name and price:
            logger.info(f"✅ {name[:30]}... - {price} {site_config['currency']}")
        elif name:
            logger.info(f"✅ Название: {name[:30]}... (цена не найдена)")
        elif price:
            logger.info(f"✅ Цена: {price} (название не найдено)")

        return price, name


def get_working_test_urls() -> List[str]:
    """Возвращает только ГАРАНТИРОВАННО РАБОЧИЕ тестовые URL"""
    return [
        "http://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        "http://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html",
        "http://books.toscrape.com/catalogue/soumission_998/index.html",
        "http://books.toscrape.com/catalogue/sharp-objects_997/index.html",
        "http://books.toscrape.com/catalogue/sapiens-a-brief-history-of-humankind_996/index.html",
    ]


if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    print("\n" + "=" * 70)
    print("📚 ТЕСТИРОВАНИЕ ПАРСЕРА (ТОЛЬКО РАБОЧИЕ САЙТЫ)")
    print("=" * 70)

    # Создаем парсер
    scraper = SiteScraper()

    # Получаем рабочие URL
    test_urls = get_working_test_urls()

    print(f"\n🔍 Найдено рабочих URL: {len(test_urls)}")
    print("-" * 70)

    # Тестируем каждый URL
    successful = 0
    failed = 0

    for i, url in enumerate(test_urls, 1):
        print(f"\n📌 Тест {i}:")
        print(f"   {url}")

        price, name = scraper.get_product_info(url)

        if price is not None and name is not None:
            successful += 1
            print(f"   ✅ УСПЕХ: {name[:40]}... - {price} £")
        else:
            failed += 1
            print(f"   ❌ НЕУДАЧА")

    # Итоги
    print("\n" + "=" * 70)
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 70)
    print(f"✅ Успешно: {successful}")
    print(f"❌ Неудачно: {failed}")
    print(f"📈 Процент успеха: {successful / len(test_urls) * 100:.1f}%")
    print("=" * 70)

    # Информация о поддержке
    print("\nℹ️ Поддерживаемые сайты:")
    for domain, info in SiteScraper.WORKING_SITES.items():
        print(f"  • {info['name']} ({domain})")

    print("\n⚠️ Demoblaze временно исключен из-за изменения структуры сайта")
    print("=" * 70)
]

Проблемы:
- Обрабатывает только 10 страниц в минуту
- Иногда падает с ошибками соединения
- Не показывает прогресс

Проанализируй код и предложи оптимизации:
1. Как ускорить работу (может, использовать параллельные запросы?)
2. Как улучшить обработку ошибок
3. Как добавить прогресс-бар
4. Как избежать блокировки (добавить прокси или ротацию User-Agent)

Напиши улучшенную версию с объяснением каждого изменения.
```
'''

"""
Модуль для парсинга цен и названий товаров с веб-страниц.
ОПТИМИЗИРОВАННАЯ ВЕРСИЯ с параллельными запросами и прогресс-баром.
"""

import requests
from bs4 import BeautifulSoup
import logging
import re
from typing import Optional, Tuple, List, Dict, Any
from urllib.parse import urlparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from queue import Queue
import random
from tqdm import tqdm
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from functools import lru_cache
import sys
import os

# Добавляем путь к оригинальному парсеру
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Настройка логирования
logger = logging.getLogger(__name__)

# Константы
DEFAULT_TIMEOUT = 15
MAX_RETRIES = 3
RETRY_BACKOFF = 0.5
MAX_WORKERS = 5  # Количество параллельных потоков
REQUEST_DELAY = 0.5  # Минимальная задержка между запросами
CACHE_SIZE = 100  # Размер кэша

# Список User-Agent для ротации
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]


class PriceParsingError(Exception):
    """Исключение при ошибках парсинга цен"""
    pass


class RateLimiter:
    """Класс для ограничения скорости запросов"""

    def __init__(self, max_requests_per_second=2):
        self.max_requests_per_second = max_requests_per_second
        self.min_interval = 1.0 / max_requests_per_second
        self.last_request_time = 0
        self.lock = Lock()

    def wait_if_needed(self):
        """Ожидание, если нужно соблюсти лимит запросов"""
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)
            self.last_request_time = time.time()


class RequestManager:
    """Менеджер HTTP запросов с поддержкой повторных попыток и ротации User-Agent"""

    def __init__(self, timeout=DEFAULT_TIMEOUT, retries=MAX_RETRIES):
        self.timeout = timeout
        self.retries = retries
        self.session_pool = Queue()
        self.user_agents = USER_AGENTS.copy()
        self.rate_limiter = RateLimiter(max_requests_per_second=2)

        # Создаем пул сессий
        for _ in range(MAX_WORKERS):
            self.session_pool.put(self._create_session())

    def _create_session(self) -> requests.Session:
        """Создание новой сессии с настройками"""
        session = requests.Session()

        # Настройка повторных попыток
        retry_strategy = Retry(
            total=self.retries,
            backoff_factor=RETRY_BACKOFF,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )

        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=MAX_WORKERS,
            pool_maxsize=MAX_WORKERS
        )

        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _get_random_user_agent(self) -> str:
        """Получение случайного User-Agent"""
        return random.choice(self.user_agents)

    def get(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Выполнение GET запроса с ротацией User-Agent и повторными попытками"""

        # Применяем rate limiting
        self.rate_limiter.wait_if_needed()

        # Получаем сессию из пула
        session = self.session_pool.get()

        try:
            # Обновляем User-Agent
            session.headers.update({
                'User-Agent': self._get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': random.choice(['en-US,en;q=0.9', 'ru-RU,ru;q=0.8,en;q=0.5']),
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            })

            # Добавляем случайную задержку для имитации человека
            time.sleep(random.uniform(0.1, 0.3))

            response = session.get(
                url,
                timeout=self.timeout,
                allow_redirects=True,
                **kwargs
            )

            return response

        except Exception as e:
            logger.debug(f"Ошибка запроса {url}: {e}")
            return None

        finally:
            # Возвращаем сессию в пул
            self.session_pool.put(session)


class SiteScraper:
    """
    Класс для парсинга информации о товарах с веб-страниц.
    Оптимизированная версия с кэшированием и параллельными запросами.
    """

    # Только ГАРАНТИРОВАННО РАБОЧИЕ сайты
    WORKING_SITES = {
        'books.toscrape.com': {
            'name': 'Books to Scrape',
            'base_url': 'http://books.toscrape.com/',
            'product_pattern': '/catalogue/',
            'selectors': {
                'price': '.price_color',
                'name': 'h1',
            },
            'price_pattern': r'£(\d+\.\d{2})',
            'currency': '£'
        }
    }

    def __init__(self, config: dict = None):
        """Инициализация парсера с оптимизациями"""
        self.config = config or {}
        self.request_manager = RequestManager(
            timeout=self.config.get('timeout', DEFAULT_TIMEOUT),
            retries=self.config.get('retries', MAX_RETRIES)
        )

        # Кэш для результатов
        self.cache = {}
        self.cache_lock = Lock()
        self.cache_enabled = self.config.get('cache_enabled', True)

        # Статистика
        self.stats = {
            'requests': 0,
            'cache_hits': 0,
            'errors': 0,
            'success': 0
        }
        self.stats_lock = Lock()

    @lru_cache(maxsize=CACHE_SIZE)
    def _get_site_config(self, domain: str) -> Optional[Dict]:
        """Получение конфигурации для сайта с кэшированием"""
        for d, config in self.WORKING_SITES.items():
            if d in domain:
                return config
        return None

    def _get_from_cache(self, url: str) -> Optional[Tuple[Optional[float], Optional[str]]]:
        """Получение данных из кэша"""
        if not self.cache_enabled:
            return None

        with self.cache_lock:
            if url in self.cache:
                with self.stats_lock:
                    self.stats['cache_hits'] += 1
                return self.cache[url]
        return None

    def _save_to_cache(self, url: str, data: Tuple[Optional[float], Optional[str]]):
        """Сохранение данных в кэш"""
        if not self.cache_enabled:
            return

        with self.cache_lock:
            if len(self.cache) >= CACHE_SIZE:
                # Удаляем случайный элемент при переполнении кэша
                random_key = random.choice(list(self.cache.keys()))
                del self.cache[random_key]
            self.cache[url] = data

    def is_site_supported(self, url: str) -> Tuple[bool, str]:
        """
        Проверяет, поддерживается ли сайт.

        Returns:
            Tuple[bool, str]: (поддерживается ли, название сайта или причина отказа)
        """
        domain = urlparse(url).netloc.replace('www.', '')

        for supported_domain, site_info in self.WORKING_SITES.items():
            if supported_domain in domain:
                # Проверяем, что это страница товара
                if site_info.get('product_pattern') in url:
                    return True, site_info['name']
                else:
                    return False, f"Это не страница товара для {site_info['name']}"

        return False, f"Сайт {domain} не поддерживается"

    def extract_price(self, text: str, pattern: str) -> Optional[float]:
        """Извлекает цену из текста"""
        try:
            match = re.search(pattern, text)
            if match:
                price_str = match.group(1) if match.groups() else match.group(0)
                price_str = price_str.replace(',', '').replace(' ', '')
                return float(price_str)
        except (ValueError, AttributeError) as e:
            logger.debug(f"Ошибка преобразования цены: {e}")
        return None

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Асинхронное получение страницы с обработкой ошибок"""

        # Проверяем кэш
        cached_result = self._get_from_cache(url)
        if cached_result:
            return cached_result

        # Проверяем поддержку сайта
        supported, site_name = self.is_site_supported(url)
        if not supported:
            logger.warning(f"⛔ {site_name}")
            with self.stats_lock:
                self.stats['errors'] += 1
            return None

        # Выполняем запрос
        response = self.request_manager.get(url)

        with self.stats_lock:
            self.stats['requests'] += 1

        if response and response.status_code == 200:
            with self.stats_lock:
                self.stats['success'] += 1
            return BeautifulSoup(response.text, 'html.parser')
        else:
            with self.stats_lock:
                self.stats['errors'] += 1
            return None

    def get_product_info(self, url: str) -> Tuple[Optional[float], Optional[str]]:
        """Получает и цену, и название за один запрос"""

        # Проверяем кэш
        cached = self._get_from_cache(url)
        if cached:
            return cached

        soup = self.fetch_page(url)
        if not soup:
            return None, None

        # Получаем настройки для сайта
        domain = urlparse(url).netloc.replace('www.', '')
        site_config = self._get_site_config(domain)

        if not site_config:
            return None, None

        # Извлекаем название
        name = None
        name_element = soup.select_one(site_config['selectors']['name'])
        if name_element:
            name = name_element.get_text(strip=True)

        # Извлекаем цену
        price = None
        price_element = soup.select_one(site_config['selectors']['price'])
        if price_element:
            price_text = price_element.get_text(strip=True)
            price = self.extract_price(price_text, site_config['price_pattern'])

        result = (price, name)

        # Сохраняем в кэш
        self._save_to_cache(url, result)

        return result

    def process_urls_parallel(self, urls: List[str], max_workers: int = MAX_WORKERS,
                              show_progress: bool = True) -> List[Dict[str, Any]]:
        """
        Параллельная обработка нескольких URL с прогресс-баром

        Args:
            urls: Список URL для обработки
            max_workers: Максимальное количество параллельных потоков
            show_progress: Показывать ли прогресс-бар

        Returns:
            List[Dict]: Результаты обработки
        """
        results = []

        # Создаем прогресс-бар
        progress_bar = tqdm(
            total=len(urls),
            desc="Обработка URL",
            unit="url",
            ncols=100,
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
        ) if show_progress else None

        # Используем ThreadPoolExecutor для параллельных запросов
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Отправляем все задачи на выполнение
            future_to_url = {
                executor.submit(self.get_product_info, url): url
                for url in urls
            }

            # Собираем результаты по мере выполнения
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    price, name = future.result(timeout=30)

                    result = {
                        'url': url,
                        'price': price,
                        'name': name,
                        'success': price is not None and name is not None,
                        'error': None
                    }

                except Exception as e:
                    result = {
                        'url': url,
                        'price': None,
                        'name': None,
                        'success': False,
                        'error': str(e)
                    }

                results.append(result)

                # Обновляем прогресс-бар
                if progress_bar:
                    progress_bar.update(1)
                    progress_bar.set_postfix({
                        'успех': sum(1 for r in results if r['success']),
                        'ошибок': sum(1 for r in results if not r['success'])
                    })

        if progress_bar:
            progress_bar.close()

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики работы парсера"""
        with self.stats_lock:
            stats = self.stats.copy()
            stats['cache_size'] = len(self.cache)
            stats['cache_hit_rate'] = (
                (stats['cache_hits'] / stats['requests'] * 100)
                if stats['requests'] > 0 else 0
            )
            stats['success_rate'] = (
                (stats['success'] / stats['requests'] * 100)
                if stats['requests'] > 0 else 0
            )
            return stats

    def clear_cache(self):
        """Очистка кэша"""
        with self.cache_lock:
            self.cache.clear()
        logger.info("🧹 Кэш очищен")


def get_working_test_urls() -> List[str]:
    """Возвращает только ГАРАНТИРОВАННО РАБОЧИЕ тестовые URL"""
    return [
        "http://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        "http://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html",
        "http://books.toscrape.com/catalogue/soumission_998/index.html",
        "http://books.toscrape.com/catalogue/sharp-objects_997/index.html",
        "http://books.toscrape.com/catalogue/sapiens-a-brief-history-of-humankind_996/index.html",
        "http://books.toscrape.com/catalogue/the-requiem-red_995/index.html",
        "http://books.toscrape.com/catalogue/the-black-mage_994/index.html",
        "http://books.toscrape.com/catalogue/libertarianism-for-beginners_993/index.html",
        "http://books.toscrape.com/catalogue/its-only-the-himalayas_992/index.html",
        "http://books.toscrape.com/catalogue/full-moon-over-noahs-ark-an-odyssey-to-mount-ararat-and-beyond_991/index.html",
    ]


def import_original_scraper():
    """
    Импортирует оригинальный парсер по указанному пути
    """
    try:
        # Путь к оригинальному парсеру
        original_parser_path = r"../../LEVEL_4_MONITORING_SYSTEM_of_PRICE/Stage_2_Parser_of_price/scraper.py"

        # Получаем абсолютный путь
        base_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_dir, original_parser_path)

        # Нормализуем путь (заменяем / на \ для Windows)
        full_path = os.path.normpath(full_path)

        # Добавляем директорию в sys.path
        module_dir = os.path.dirname(full_path)
        if module_dir not in sys.path:
            sys.path.insert(0, module_dir)

        # Импортируем модуль
        import importlib.util
        spec = importlib.util.spec_from_file_location("original_parser", full_path)
        if spec and spec.loader:
            original_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(original_module)
            return original_module.SiteScraper
        else:
            raise ImportError(f"Не удалось загрузить модуль из {full_path}")

    except Exception as e:
        print(f"❌ Ошибка при импорте оригинального парсера: {e}")
        print(f"   Путь: {full_path if 'full_path' in locals() else 'не определен'}")
        return None


def benchmark_original_vs_optimized():
    """Сравнение производительности оригинальной и оптимизированной версий"""

    print("\n" + "=" * 80)
    print("📊 СРАВНЕНИЕ ПРОИЗВОДИТЕЛЬНОСТИ")
    print("=" * 80)

    # Импортируем оригинальный парсер
    OriginalScraper = import_original_scraper()

    if OriginalScraper is None:
        print("\n❌ Не удалось загрузить оригинальный парсер.")
        print("   Проверьте путь к файлу scraper.py")
        print(f"   Текущая директория: {os.path.abspath('../../../..')}")
        return

    # Получаем тестовые URL
    urls = get_working_test_urls()

    # Тест оригинальной версии (последовательная)
    print("\n🔴 ОРИГИНАЛЬНАЯ ВЕРСИЯ (последовательная)")
    print("-" * 80)

    try:
        original_scraper = OriginalScraper()
        start_time = time.time()

        successful_original = 0
        for i, url in enumerate(urls, 1):
            print(f"\r  Обработка {i}/{len(urls)}...", end="")
            try:
                # В зависимости от интерфейса оригинального парсера
                if hasattr(original_scraper, 'get_product_info'):
                    price, name = original_scraper.get_product_info(url)
                elif hasattr(original_scraper, 'get_price') and hasattr(original_scraper, 'get_product_name'):
                    price = original_scraper.get_price(url)
                    name = original_scraper.get_product_name(url)
                else:
                    # Пробуем другие возможные методы
                    price = None
                    name = None

                if price is not None and name is not None:
                    successful_original += 1
            except Exception as e:
                logger.debug(f"Ошибка при обработке {url}: {e}")

        print()  # Переход на новую строку
        original_time = time.time() - start_time

        # Тест оптимизированной версии (параллельная)
        print("\n🟢 ОПТИМИЗИРОВАННАЯ ВЕРСИЯ (параллельная)")
        print("-" * 80)

        optimized_scraper = SiteScraper()
        start_time = time.time()

        results = optimized_scraper.process_urls_parallel(urls, show_progress=True)
        successful_optimized = sum(1 for r in results if r['success'])

        optimized_time = time.time() - start_time

        # Вывод результатов сравнения
        print("\n" + "=" * 80)
        print("📈 РЕЗУЛЬТАТЫ СРАВНЕНИЯ")
        print("=" * 80)
        print(f"📊 Количество URL: {len(urls)}")
        print(f"\n🔴 Оригинальная версия:")
        print(f"   ⏱️  Время: {original_time:.2f} сек")
        print(f"   ✅ Успешно: {successful_original}/{len(urls)}")
        print(f"   📈 Скорость: {len(urls) / original_time:.1f} URL/сек")

        print(f"\n🟢 Оптимизированная версия:")
        print(f"   ⏱️  Время: {optimized_time:.2f} сек")
        print(f"   ✅ Успешно: {successful_optimized}/{len(urls)}")
        print(f"   📈 Скорость: {len(urls) / optimized_time:.1f} URL/сек")

        if optimized_time > 0:
            print(f"\n🚀 Ускорение: {original_time / optimized_time:.1f}x")
        else:
            print(f"\n🚀 Ускорение: ∞ (оптимизированная версия мгновенна)")

    except Exception as e:
        print(f"\n❌ Ошибка при выполнении сравнения: {e}")
        import traceback
        traceback.print_exc()

    print("=" * 80)


if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    print("\n" + "=" * 80)
    print("📚 ТЕСТИРОВАНИЕ ОПТИМИЗИРОВАННОГО ПАРСЕРА")
    print("=" * 80)

    # Создаем парсер
    scraper = SiteScraper()

    # Получаем рабочие URL
    test_urls = get_working_test_urls()

    print(f"\n🔍 Найдено рабочих URL: {len(test_urls)}")

    # Тестируем параллельную обработку
    results = scraper.process_urls_parallel(test_urls, max_workers=5, show_progress=True)

    # Получаем статистику
    stats = scraper.get_stats()

    # Итоги
    print("\n" + "=" * 80)
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 80)
    print(f"✅ Успешно: {stats['success']}")
    print(f"❌ Ошибок: {stats['errors']}")
    print(f"📈 Процент успеха: {stats['success_rate']:.1f}%")
    print(f"💾 Попаданий в кэш: {stats['cache_hits']}")
    print(f"📊 Размер кэша: {stats['cache_size']}")
    print(f"🎯 Процент попаданий: {stats['cache_hit_rate']:.1f}%")

    if stats['requests'] > 0:
        print(f"⏱️  Скорость: {len(test_urls) / stats['requests'] * stats['success_rate'] / 100:.1f} URL/сек")

    print("=" * 80)

    # Информация о поддержке
    print("\nℹ️ Поддерживаемые сайты:")
    for domain, info in SiteScraper.WORKING_SITES.items():
        print(f"  • {info['name']} ({domain})")

    print("\n🚀 ОПТИМИЗАЦИИ ВНЕДРЕНЫ:")
    print("  • Параллельные запросы (ThreadPoolExecutor)")
    print("  • Кэширование результатов (LRU cache)")
    print("  • Прогресс-бар (tqdm)")
    print("  • Ротация User-Agent")
    print("  • Пул соединений")
    print("  • Rate limiting")
    print("  • Повторные попытки при ошибках")
    print("  • Статистика производительности")
    print("=" * 80)

    # Спрашиваем, хочет ли пользователь запустить бенчмарк
    try:
        response = input("\n🔄 Запустить сравнение с оригинальной версией? (y/n): ")
        if response.lower() == 'y':
            benchmark_original_vs_optimized()
    except KeyboardInterrupt:
        print("\n\n👋 Выход")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")