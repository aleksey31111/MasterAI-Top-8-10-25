#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Задача 3.2: Обход Cloudflare
Цель: Научиться использовать специализированные библиотеки.

Промпт для ИИ:
```
Некоторые сайты защищены Cloudflare. Напиши скрипт, который демонстрирует разницу между обычным requests и библиотекой cloudscraper.

Задачи:
1. Попробуй получить страницу любого сайта с Cloudflare защитой (например, https://nowsecure.nl/ - тестовый сайт)
   - Сначала обычным requests
   - Затем с помощью cloudscraper
2. Сравни статус-коды и наличие контента
3. Извлеки заголовок страницы при успешном запросе
4. Сохрани успешный HTML в файл
5. Добавь ротацию User-Agent (использовать разные заголовки)
6. Выведи сравнительную таблицу результатов

Дополнительно: добавь обработку таймаутов и повторных попыток
```
'''
"""
Демонстрация разницы между requests и cloudscraper для обхода Cloudflare.
Исправленная версия с лучшей обработкой ошибок и альтернативными сайтами.
"""

import requests
import cloudscraper
import random
import time
from datetime import datetime
from typing import Dict, Tuple, Optional, List
import os
import socket
import ssl


class CloudflareBypassDemo:
    """
    Класс для демонстрации обхода Cloudflare защиты
    """

    # Список тестовых сайтов с Cloudflare защитой
    TEST_SITES = [
        "https://nowsecure.nl/",  # Специально для тестов
        "https://cf-test.sy1.me/",  # Альтернативный тестовый сайт
        "https://cloudflare.com/",  # Официальный сайт Cloudflare
        "https://www.cloudflare.com/",  # Тоже Cloudflare
    ]

    # Список различных User-Agent для ротации
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7; rv:109.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
    ]

    def __init__(self, target_url: str = None):
        """
        Инициализация демонстратора

        Args:
            target_url: URL для тестирования (если None, будет выбран из списка)
        """
        self.target_url = target_url or random.choice(self.TEST_SITES)
        self.session = requests.Session()

        # Настройка cloudscraper с дополнительными параметрами
        self.scraper = cloudscraper.create_scraper(
            interpreter='native',  # Использовать встроенный интерпретатор JS
            delay=15,  # Увеличенная задержка для решения задач
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True,
                'mobile': False
            }
        )

        self.results = {}

    def get_random_user_agent(self) -> str:
        """Возвращает случайный User-Agent из списка"""
        return random.choice(self.USER_AGENTS)

    def setup_headers(self) -> Dict:
        """Формирует заголовки с ротацией User-Agent"""
        return {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }

    def check_connection(self) -> bool:
        """Проверяет базовое соединение с сайтом"""
        try:
            host = self.target_url.replace('https://', '').replace('http://', '').split('/')[0]
            socket.create_connection((host, 443), timeout=5)
            print(f"  ✅ Базовое соединение с {host} установлено")
            return True
        except Exception as e:
            print(f"  ❌ Нет соединения с хостом: {e}")
            return False

    def try_requests(self, max_retries: int = 3) -> Tuple[int, Optional[str], float]:
        """Пытается получить страницу через обычный requests"""
        print("  📡 Используем обычный requests...")

        for attempt in range(1, max_retries + 1):
            try:
                start_time = time.time()

                # Меняем User-Agent при каждой попытке
                headers = self.setup_headers()
                print(f"    Попытка {attempt}: User-Agent: {headers['User-Agent'][:50]}...")

                # Увеличиваем таймауты
                response = self.session.get(
                    self.target_url,
                    headers=headers,
                    timeout=(10, 30),  # (connect timeout, read timeout)
                    allow_redirects=True,
                    verify=True
                )

                end_time = time.time()
                response_time = round(end_time - start_time, 2)

                # Проверяем размер ответа (иногда приходят пустые страницы)
                content_length = len(response.content)
                print(f"    Размер ответа: {content_length} байт")

                if content_length < 1000 and response.status_code == 200:
                    print(f"    ⚠️ Подозрительно маленький ответ")

                return response.status_code, response.text, response_time

            except requests.exceptions.Timeout as e:
                print(f"    ⏱️ Таймаут: {e} (попытка {attempt})")
            except requests.exceptions.ConnectionError as e:
                print(f"    🔌 Ошибка соединения: {e} (попытка {attempt})")
            except requests.exceptions.SSLError as e:
                print(f"    🔒 Ошибка SSL: {e} (попытка {attempt})")
            except Exception as e:
                print(f"    ❌ Ошибка: {type(e).__name__}: {e} (попытка {attempt})")

            # Экспоненциальная задержка между попытками
            if attempt < max_retries:
                wait_time = 2 ** attempt  # 2, 4, 8 секунд
                print(f"    ⏳ Ожидание {wait_time} сек перед следующей попыткой...")
                time.sleep(wait_time)

        return 0, None, 0.0

    def try_cloudscraper(self, max_retries: int = 3) -> Tuple[int, Optional[str], float]:
        """Пытается получить страницу через cloudscraper"""
        print("  ☁️ Используем cloudscraper...")

        for attempt in range(1, max_retries + 1):
            try:
                start_time = time.time()

                # cloudscraper автоматически управляет заголовками
                headers = {'User-Agent': self.get_random_user_agent()}

                # Увеличиваем таймауты для cloudscraper
                response = self.scraper.get(
                    self.target_url,
                    headers=headers,
                    timeout=(10, 45),  # Больше времени на чтение для решения задач
                    allow_redirects=True
                )

                end_time = time.time()
                response_time = round(end_time - start_time, 2)

                # Проверяем, не вернул ли cloudscraper страницу с ошибкой
                content_length = len(response.content)
                print(f"    Размер ответа: {content_length} байт")

                # Проверяем, не содержит ли ответ признаки ошибки
                if "Access denied" in response.text or "403 Forbidden" in response.text:
                    print(f"    ⚠️ Получена страница с ошибкой доступа")

                return response.status_code, response.text, response_time

            except cloudscraper.exceptions.CloudflareChallengeError as e:
                print(f"    ☁️ Ошибка Cloudflare challenge: {e} (попытка {attempt})")
            except requests.exceptions.Timeout as e:
                print(f"    ⏱️ Таймаут: {e} (попытка {attempt})")
            except requests.exceptions.ConnectionError as e:
                print(f"    🔌 Ошибка соединения: {e} (попытка {attempt})")
            except Exception as e:
                print(f"    ❌ Ошибка cloudscraper: {type(e).__name__}: {e} (попытка {attempt})")

            if attempt < max_retries:
                wait_time = 3 * attempt  # 3, 6, 9 секунд
                print(f"    ⏳ Ожидание {wait_time} сек перед следующей попыткой...")
                time.sleep(wait_time)

        return 0, None, 0.0

    def extract_title(self, html_content: str) -> str:
        """Извлекает заголовок страницы из HTML"""
        if not html_content:
            return "Нет контента"

        # Простой поиск title
        import re

        # Ищем стандартный title
        title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
        if title_match:
            return title_match.group(1).strip()[:80]

        # Ищем другие признаки
        if "Checking your browser" in html_content:
            return "⚠️ СТРАНИЦА ПРОВЕРКИ BROWSER CHECKING"
        elif "cf-browser-verification" in html_content:
            return "⚠️ CLOUDFLARE BROWSER VERIFICATION"
        elif "Access denied" in html_content or "403" in html_content:
            return "⛔ ACCESS DENIED (403)"
        elif "Just a moment" in html_content:
            return "⏳ JUST A MOMENT - Cloudflare"
        elif "DDoS" in html_content or "attack" in html_content:
            return "🛡️ DDoS PROTECTION PAGE"
        elif len(html_content) < 500:
            return f"⚠️ ПУСТАЯ СТРАНИЦА ({len(html_content)} байт)"
        else:
            # Пробуем найти h1
            h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_content, re.IGNORECASE | re.DOTALL)
            if h1_match:
                return f"h1: {h1_match.group(1).strip()[:50]}"

        return f"Контент получен ({len(html_content)} байт)"

    def save_html(self, content: str, method: str) -> str:
        """Сохраняет HTML в файл"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{method}_result_{timestamp}.html"

        os.makedirs("results", exist_ok=True)
        filepath = os.path.join("results", filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return filepath

    def try_alternative_site(self) -> bool:
        """Пробует альтернативный сайт, если первый не работает"""
        print("\n🔄 Пробуем альтернативный тестовый сайт...")

        for site in self.TEST_SITES[1:]:  # Пропускаем первый (nowsecure.nl)
            print(f"\n📌 Тестируем: {site}")
            self.target_url = site

            # Быстрая проверка доступности
            if not self.check_connection():
                continue

            # Пробуем cloudscraper
            status, content, resp_time = self.try_cloudscraper(max_retries=2)

            if status == 200 and content and len(content) > 1000:
                print(f"✅ Найден рабочий сайт: {site}")
                return True

            print(f"❌ Сайт {site} не работает должным образом")

        return False

    def run_demo(self):
        """Запускает демонстрацию сравнения методов"""
        print("\n" + "=" * 80)
        print("🔍 ДЕМОНСТРАЦИЯ ОБХОДА CLOUDFLARE ЗАЩИТЫ (ИСПРАВЛЕННАЯ ВЕРСИЯ)")
        print("=" * 80)
        print(f"🎯 Тестовый URL: {self.target_url}")
        print(f"🕒 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        # Проверяем базовое соединение
        print("\n🔌 ПРОВЕРКА СОЕДИНЕНИЯ")
        print("-" * 40)
        if not self.check_connection():
            print("⚠️ Проблемы с соединением, пробуем альтернативный сайт...")
            if not self.try_alternative_site():
                print("❌ Не удалось найти рабочий тестовый сайт")
                return

        # Тест 1: Обычный requests
        print("\n📦 ТЕСТ 1: Обычный requests")
        print("-" * 40)
        requests_status, requests_content, requests_time = self.try_requests(max_retries=3)
        requests_title = self.extract_title(requests_content) if requests_content else "Нет данных"

        # Тест 2: cloudscraper
        print("\n☁️ ТЕСТ 2: cloudscraper")
        print("-" * 40)
        scraper_status, scraper_content, scraper_time = self.try_cloudscraper(max_retries=3)
        scraper_title = self.extract_title(scraper_content) if scraper_content else "Нет данных"

        # Сохраняем результаты
        saved_files = []
        if scraper_content and scraper_status == 200:
            filename = self.save_html(scraper_content, "cloudscraper")
            saved_files.append(filename)
            print(f"\n💾 HTML сохранен: results/{filename}")

        if requests_content and requests_status == 200:
            filename = self.save_html(requests_content, "requests")
            saved_files.append(filename)
            print(f"💾 HTML сохранен: results/{filename}")

        # Вывод сравнительной таблицы
        print("\n" + "=" * 80)
        print("📊 СРАВНИТЕЛЬНАЯ ТАБЛИЦА РЕЗУЛЬТАТОВ")
        print("=" * 80)

        headers = ["Метод", "Статус", "Время (сек)", "Заголовок страницы/Результат"]
        data = [
            ["requests", requests_status, requests_time, requests_title[:60]],
            ["cloudscraper", scraper_status, scraper_time, scraper_title[:60]]
        ]

        # Вывод таблицы
        col_widths = [max(len(str(row[i])) for row in [headers] + data) for i in range(len(headers))]
        header_row = " | ".join(f"{headers[i]:<{col_widths[i]}}" for i in range(len(headers)))
        print(header_row)
        print("-" * len(header_row))

        for row in data:
            print(" | ".join(f"{str(row[i]):<{col_widths[i]}}" for i in range(len(row))))

        print("=" * 80)

        # Анализ результатов
        print("\n🔎 АНАЛИЗ РЕЗУЛЬТАТОВ:")

        # Для requests
        if requests_status in [403,
                               503] or "Checking your browser" in requests_title or "Just a moment" in requests_title:
            print("✅ requests: Заблокирован Cloudflare (ожидаемо)")
        elif requests_status == 200 and len(requests_content or '') > 5000:
            print("⚠️ requests: Странно, но получил контент")
        else:
            print("ℹ️ requests: Не удалось получить данные")

        # Для cloudscraper
        if scraper_status == 200 and scraper_content and len(scraper_content) > 5000:
            print("✅ cloudscraper: Успешно обошел защиту")
        elif scraper_status == 200 and "Checking your browser" in (scraper_title or ''):
            print("⚠️ cloudscraper: Получил страницу проверки")
        elif scraper_status == 403:
            print("❌ cloudscraper: Заблокирован (нужны дополнительные настройки)")
        else:
            print("❌ cloudscraper: Не удалось обойти защиту")

        # Информация о ротации User-Agent
        print(f"\n🔄 Ротация User-Agent: использовано {len(set(self.USER_AGENTS))} различных вариантов")

        if saved_files:
            print(f"\n📁 Файлы сохранены в папке 'results'")

        return {
            'requests': {'status': requests_status, 'title': requests_title, 'time': requests_time},
            'cloudscraper': {'status': scraper_status, 'title': scraper_title, 'time': scraper_time},
            'saved_files': saved_files,
            'url': self.target_url
        }


def main():
    """Главная функция"""

    # Можно указать конкретный URL или оставить None для случайного выбора
    demo = CloudflareBypassDemo()  # Без аргумента - выберет случайный

    try:
        results = demo.run_demo()

        print("\n" + "=" * 80)
        print("✅ Демонстрация завершена")
        print("=" * 80)

        # Если не удалось, даем рекомендации
        if results and results['cloudscraper']['status'] != 200:
            print("\n💡 РЕКОМЕНДАЦИИ:")
            print("1. Проверьте интернет-соединение")
            print("2. Попробуйте использовать VPN (некоторые регионы блокируют Cloudflare)")
            print("3. Запустите скрипт через 10-15 минут (возможны временные проблемы)")
            print("4. Попробуйте другой тестовый сайт из списка")

    except KeyboardInterrupt:
        print("\n\n⚠️ Прерывание пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()