#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Задача 2.2: Парсер вакансий с параметрами
Цель: Научиться создавать гибкие скрипты с аргументами командной строки.

Промпт для ИИ:
```
Разработай скрипт для парсинга вакансий с сайта https://realpython.github.io/fake-jobs/.

Скрипт должен принимать аргументы командной строки:
--query (или -q): поисковый запрос (например, "python")
--location (или -l): город (например, "London")
--pages (или -p): количество страниц для парсинга (по умолчанию 1)
--output (или -o): формат вывода (csv или json, по умолчанию csv)

Для каждой вакансии собрать:
- Название должности
- Компанию
- Локацию
- Дату публикации
- Ссылку на детальную страницу

Логика работы:
1. Сформировать URL с учетом параметров поиска
2. Для каждой страницы извлечь вакансии
3. Если указано несколько страниц, обработать пагинацию
4. Сохранить результат в указанном формате
5. Добавить логирование в файл scraper.log

Пример запуска:
python Basket/1_03_2026_Practice_Of_32_Lesson/LEVEL_1_BEGINNER_Learning_to_set_simple_tasks/Task_2_2_Parser_jobs_with_options/job_parser.py --query "python developer" --location "London" --pages 3 --output json
```
'''
"""
Парсер вакансий с сайта https://realpython.github.io/fake-jobs/
Поддерживает поиск по запросу, локации, пагинацию и сохранение в CSV/JSON.
"""

import argparse
import requests
from bs4 import BeautifulSoup
import csv
import json
import logging
import time
import sys
from urllib.parse import urljoin, urlencode
from datetime import datetime
from typing import List, Dict, Optional

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('job_parser')


class JobScraper:
    """Класс для парсинга вакансий с Fake Jobs сайта"""

    BASE_URL = "https://realpython.github.io/fake-jobs/"

    def __init__(self, query: str = "", location: str = "", pages: int = 1):
        """
        Инициализация парсера

        Args:
            query: Поисковый запрос (фильтр по названию)
            location: Город для фильтрации
            pages: Количество страниц для парсинга
        """
        self.query = query.lower() if query else ""
        self.location = location.lower() if location else ""
        self.pages = pages
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def check_site_availability(self) -> bool:
        """
        Проверка доступности сайта перед началом парсинга

        Returns:
            bool: Доступен ли сайт
        """
        try:
            logger.info(f"Проверка доступности сайта {self.BASE_URL}")
            response = self.session.get(self.BASE_URL, timeout=5)
            response.raise_for_status()
            logger.info("✅ Сайт доступен")
            return True
        except requests.exceptions.ConnectionError:
            logger.error("❌ Сайт недоступен: ошибка подключения")
            return False
        except requests.exceptions.Timeout:
            logger.error("❌ Сайт недоступен: таймаут")
            return False
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ Сайт вернул ошибку HTTP: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка при проверке сайта: {e}")
            return False

    def build_search_url(self, page: int = 1) -> str:
        """
        Формирование URL с учетом параметров поиска (разные способы)

        Args:
            page: Номер страницы

        Returns:
            str: Сформированный URL
        """
        # Способ 1: Простое добавление параметров к базовому URL
        # На этом сайте нет реальной фильтрации, поэтому имитируем её

        if page == 1:
            url = self.BASE_URL
        else:
            # На сайте пагинация через page/2/, page/3/ и т.д.
            url = f"{self.BASE_URL}page/{page}/"

        # Добавляем параметры как GET-параметры для имитации фильтрации
        # (сайт их не обрабатывает, но для демонстрации оставим)
        params = {}
        if self.query:
            params['q'] = self.query
        if self.location:
            params['loc'] = self.location

        if params:
            url += "?" + urlencode(params)

        logger.debug(f"Сформирован URL: {url}")
        return url

    def parse_jobs_from_page(self, url: str) -> List[Dict]:
        """
        Парсинг вакансий с одной страницы

        Args:
            url: URL страницы для парсинга

        Returns:
            List[Dict]: Список вакансий
        """
        jobs = []

        try:
            logger.info(f"Парсинг страницы: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Находим все карточки вакансий
            job_cards = soup.find_all('div', class_='card-content')

            if not job_cards:
                logger.warning("На странице не найдено карточек вакансий")
                return []

            logger.info(f"Найдено карточек: {len(job_cards)}")

            for card in job_cards:
                try:
                    # Название должности
                    title_elem = card.find('h2', class_='title')
                    if not title_elem:
                        continue
                    title = title_elem.text.strip()

                    # Компания
                    company_elem = card.find('h3', class_='company')
                    company = company_elem.text.strip() if company_elem else "N/A"

                    # Локация
                    location_elem = card.find('p', class_='location')
                    location = location_elem.text.strip() if location_elem else "N/A"

                    # Дата публикации
                    date_elem = card.find('p', class_='date')
                    date = date_elem.text.strip() if date_elem else "N/A"

                    # Ссылка на детальную страницу
                    link_elem = card.find('a', string='Apply')
                    link = urljoin(self.BASE_URL, link_elem['href']) if link_elem else "N/A"

                    # Применяем фильтры (имитация поиска, так как сайт не фильтрует реально)
                    if self.query and self.query not in title.lower():
                        continue
                    if self.location and self.location not in location.lower():
                        continue

                    job = {
                        'title': title,
                        'company': company,
                        'location': location,
                        'date': date,
                        'url': link,
                        'page': url.split('/')[-2] if 'page' in url else 1
                    }

                    jobs.append(job)
                    logger.debug(f"Найдена вакансия: {title} в {company}")

                except Exception as e:
                    logger.error(f"Ошибка при парсинге карточки: {e}")
                    continue

            logger.info(f"После фильтрации: {len(jobs)} вакансий")

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при загрузке страницы {url}: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при парсинге страницы: {e}")

        return jobs

    def scrape_all_pages(self) -> List[Dict]:
        """
        Парсинг всех указанных страниц с пагинацией

        Returns:
            List[Dict]: Все собранные вакансии
        """
        all_jobs = []

        for page in range(1, self.pages + 1):
            try:
                url = self.build_search_url(page)
                page_jobs = self.parse_jobs_from_page(url)
                all_jobs.extend(page_jobs)

                # Задержка между запросами
                if page < self.pages:
                    logger.info("Ожидание 1 секунды перед следующим запросом...")
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Критическая ошибка на странице {page}: {e}")
                break

        return all_jobs

    def save_to_csv(self, jobs: List[Dict], filename: str):
        """
        Сохранение вакансий в CSV файл

        Args:
            jobs: Список вакансий
            filename: Имя файла
        """
        if not jobs:
            logger.warning("Нет данных для сохранения в CSV")
            return

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['title', 'company', 'location', 'date', 'url', 'page']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(jobs)

            logger.info(f"✅ Данные сохранены в CSV: {filename}")
            logger.info(f"   Записано записей: {len(jobs)}")

        except Exception as e:
            logger.error(f"Ошибка при сохранении CSV: {e}")

    def save_to_json(self, jobs: List[Dict], filename: str):
        """
        Сохранение вакансий в JSON файл

        Args:
            jobs: Список вакансий
            filename: Имя файла
        """
        if not jobs:
            logger.warning("Нет данных для сохранения в JSON")
            return

        try:
            output = {
                'metadata': {
                    'query': self.query,
                    'location': self.location,
                    'pages': self.pages,
                    'total_jobs': len(jobs),
                    'timestamp': datetime.now().isoformat()
                },
                'jobs': jobs
            }

            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(output, jsonfile, ensure_ascii=False, indent=2)

            logger.info(f"✅ Данные сохранены в JSON: {filename}")
            logger.info(f"   Записано записей: {len(jobs)}")

        except Exception as e:
            logger.error(f"Ошибка при сохранении JSON: {e}")


def main():
    """Главная функция программы"""

    # Настройка парсера аргументов командной строки
    parser = argparse.ArgumentParser(
        description='Парсер вакансий с сайта Fake Jobs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Примеры использования:
  python config.py --query "python" --location "London" --pages 3 --output json
  python config.py -q "developer" -l "New York" -p 2 -o csv
  python config.py --pages 5  (парсинг 5 страниц без фильтрации)
        '''
    )

    parser.add_argument(
        '--query', '-q',
        type=str,
        default='',
        help='Поисковый запрос (например, "python", "developer")'
    )

    parser.add_argument(
        '--location', '-l',
        type=str,
        default='',
        help='Город для фильтрации (например, "London", "New York")'
    )

    parser.add_argument(
        '--pages', '-p',
        type=int,
        default=1,
        help='Количество страниц для парсинга (по умолчанию: 1)'
    )

    parser.add_argument(
        '--output', '-o',
        type=str,
        choices=['csv', 'json'],
        default='csv',
        help='Формат вывода: csv или json (по умолчанию: csv)'
    )

    args = parser.parse_args()

    # Вывод параметров запуска
    logger.info("=" * 60)
    logger.info("🚀 ЗАПУСК ПАРСЕРА ВАКАНСИЙ")
    logger.info("=" * 60)
    logger.info(f"Параметры поиска:")
    logger.info(f"  Запрос: '{args.query or 'все'}'")
    logger.info(f"  Локация: '{args.location or 'все'}'")
    logger.info(f"  Страниц: {args.pages}")
    logger.info(f"  Формат: {args.output}")
    logger.info("=" * 60)

    # Создание парсера
    scraper = JobScraper(
        query=args.query,
        location=args.location,
        pages=args.pages
    )

    # Проверка доступности сайта
    if not scraper.check_site_availability():
        logger.error("Сайт недоступен. Завершение работы.")
        sys.exit(1)

    # Парсинг вакансий
    logger.info("Начинаем сбор вакансий...")
    start_time = time.time()

    jobs = scraper.scrape_all_pages()

    end_time = time.time()
    logger.info("=" * 60)
    logger.info(f"📊 ИТОГИ СБОРА:")
    logger.info(f"   Найдено вакансий: {len(jobs)}")
    logger.info(f"   Время выполнения: {end_time - start_time:.2f} сек")

    if jobs:
        # Генерация имени файла
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"jobs_{timestamp}.{args.output}"

        # Сохранение результатов
        if args.output == 'csv':
            scraper.save_to_csv(jobs, filename)
        else:
            scraper.save_to_json(jobs, filename)

        # Показываем первые несколько вакансий
        logger.info("\n📋 Примеры найденных вакансий:")
        for i, job in enumerate(jobs[:5], 1):
            logger.info(f"  {i}. {job['title']} - {job['company']} ({job['location']})")

        if len(jobs) > 5:
            logger.info(f"  ... и еще {len(jobs) - 5} вакансий")

    logger.info("=" * 60)
    logger.info("✅ Парсинг завершен")


if __name__ == "__main__":
    main()