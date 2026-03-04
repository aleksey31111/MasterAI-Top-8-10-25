import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import csv
import time
from datetime import datetime
import os


class QuoteScraper:
    """
    Парсер для динамического сайта с цитатами http://quotes.toscrape.com/js/
    Использует Playwright для работы с JavaScript
    """

    def __init__(self, headless=True):
        """
        Инициализация парсера

        Args:
            headless: Режим работы браузера (True - без GUI, False - с окном)
        """
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.all_quotes = []

    async def setup_browser(self):
        """Настройка и запуск браузера в нужном режиме"""
        print("🌐 Запуск браузера...")
        self.playwright = await async_playwright().start()

        # Запуск Chrome с настройками
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )

        # Создание контекста с увеличенным таймаутом
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        self.page = await self.context.new_page()

        # Устанавливаем таймауты
        self.page.set_default_timeout(30000)  # 30 секунд для обычных операций
        self.page.set_default_navigation_timeout(45000)  # 45 секунд для навигации

        print("✅ Браузер запущен")

    async def close_browser(self):
        """Закрытие браузера"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("🌐 Браузер закрыт")

    async def take_screenshot(self, filename_prefix="error"):
        """
        Создание скриншота страницы (полезно для отладки)

        Args:
            filename_prefix: Префикс имени файла
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshots/{filename_prefix}_{timestamp}.png"

        # Создаем папку для скриншотов, если её нет
        os.makedirs("screenshots", exist_ok=True)

        await self.page.screenshot(path=filename, full_page=True)
        print(f"📸 Скриншот сохранен: {filename}")
        return filename

    async def wait_for_quotes(self, timeout=10000):
        """
        Явное ожидание загрузки цитат на странице

        Args:
            timeout: Максимальное время ожидания в миллисекундах
        """
        try:
            # Ждем появления хотя бы одной цитаты
            await self.page.wait_for_selector('.quote', timeout=timeout)
            print("✅ Цитаты загружены")
            return True
        except PlaywrightTimeoutError:
            print("❌ Таймаут ожидания цитат")
            return False

    async def parse_current_page(self):
        """
        Парсинг цитат с текущей страницы

        Returns:
            list: Список цитат с текущей страницы
        """
        # Ждем загрузки цитат
        if not await self.wait_for_quotes():
            return []

        # Находим все элементы с цитатами
        quote_elements = await self.page.query_selector_all('.quote')
        print(f"📄 Найдено цитат на странице: {len(quote_elements)}")

        page_quotes = []

        for quote_elem in quote_elements:
            try:
                # Текст цитаты
                text_elem = await quote_elem.query_selector('.text')
                text = await text_elem.inner_text() if text_elem else "N/A"

                # Автор
                author_elem = await quote_elem.query_selector('.author')
                author = await author_elem.inner_text() if author_elem else "N/A"

                # Теги
                tags = []
                tag_elements = await quote_elem.query_selector_all('.tag')
                for tag_elem in tag_elements:
                    tag = await tag_elem.inner_text()
                    tags.append(tag)

                quote_data = {
                    'text': text,
                    'author': author,
                    'tags': ', '.join(tags) if tags else 'No tags',
                    'url': self.page.url
                }

                page_quotes.append(quote_data)
                print(f"  ✓ {author}: {text[:50]}...")

            except Exception as e:
                print(f"  ❌ Ошибка при парсинге цитаты: {e}")
                await self.take_screenshot("quote_parse_error")

        return page_quotes

    async def click_next(self):
        """
        Клик по кнопке "Next" для перехода на следующую страницу

        Returns:
            bool: True если переход выполнен, False если кнопки нет или она неактивна
        """
        try:
            # Ищем кнопку Next (используем CSS-селектор для надежности)
            next_button = await self.page.query_selector('.next a')

            if not next_button:
                print("🔚 Кнопка Next не найдена")
                return False

            # Проверяем, активна ли кнопка
            is_disabled = await next_button.get_attribute('aria-disabled')
            if is_disabled == 'true':
                print("🔚 Кнопка Next неактивна (последняя страница)")
                return False

            # Получаем URL следующей страницы для логирования
            next_url = await next_button.get_attribute('href')
            print(f"➡️ Переход на следующую страницу: {next_url}")

            # Кликаем по кнопке
            await next_button.click()

            # Ждем изменения URL или загрузки новых цитат
            await self.page.wait_for_load_state('networkidle')

            # Добавляем небольшую задержку после клика (как требуется)
            await asyncio.sleep(1)

            return True

        except Exception as e:
            print(f"❌ Ошибка при клике на Next: {e}")
            await self.take_screenshot("next_button_error")
            return False

    async def scrape_all_pages(self, start_url="http://quotes.toscrape.com/js/"):
        """
        Сбор цитат со всех доступных страниц

        Args:
            start_url: Начальный URL для парсинга
        """
        print(f"\n🚀 Начинаем сбор цитат с {start_url}")
        print("=" * 60)

        page_num = 1
        has_next = True

        # Переходим на начальную страницу
        await self.page.goto(start_url)

        # Ждем загрузки
        if not await self.wait_for_quotes():
            print("❌ Не удалось загрузить начальную страницу")
            return

        while has_next:
            print(f"\n📑 Страница {page_num}")
            print("-" * 40)

            # Парсим текущую страницу
            page_quotes = await self.parse_current_page()
            self.all_quotes.extend(page_quotes)

            print(f"📊 Всего собрано: {len(self.all_quotes)} цитат")

            # Пытаемся перейти на следующую страницу
            if page_num > 1:  # Добавляем задержку между страницами (кроме первой)
                print("⏳ Задержка перед следующим запросом...")
                await asyncio.sleep(2)

            has_next = await self.click_next()
            page_num += 1

            # Защита от бесконечного цикла (максимум 20 страниц)
            if page_num > 20:
                print("⚠️ Достигнут лимит страниц (20). Останавливаемся.")
                break

        print("\n" + "=" * 60)
        print(f"✅ Сбор завершен! Всего страниц: {page_num - 1}")
        print(f"📚 Всего цитат: {len(self.all_quotes)}")

    def save_to_csv(self, filename=None):
        """
        Сохранение цитат в CSV файл

        Args:
            filename: Имя файла (если None, генерируется автоматически)
        """
        if not self.all_quotes:
            print("❌ Нет данных для сохранения")
            return

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"quotes_{timestamp}.csv"

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['text', 'author', 'tags', 'url']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.all_quotes)

            print(f"💾 Данные сохранены в файл: {filename}")
            print(f"   Размер файла: {os.path.getsize(filename)} байт")

        except Exception as e:
            print(f"❌ Ошибка при сохранении CSV: {e}")


async def main():
    """Главная асинхронная функция"""

    print("🐍 ПАРСЕР ДИНАМИЧЕСКИХ ЦИТАТ")
    print("=" * 60)

    # Создаем экземпляр парсера
    scraper = QuoteScraper(headless=True)  # True для безголового режима

    try:
        # Запускаем браузер
        await scraper.setup_browser()

        # Собираем цитаты
        await scraper.scrape_all_pages()

        # Сохраняем результаты
        scraper.save_to_csv()

    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        if scraper.page:
            await scraper.take_screenshot("critical_error")

    finally:
        # Обязательно закрываем браузер
        await scraper.close_browser()

    print("\n✅ Программа завершена")


if __name__ == "__main__":
    # Запуск асинхронной функции
    asyncio.run(main())