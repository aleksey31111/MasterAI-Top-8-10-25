'''
 Задача 3.1: Парсер с Playwright
Цель: Научиться формулировать задачи для работы с динамическими сайтами.

Промпт для ИИ:
```
Напиши парсер для динамической версии сайта с цитатами: http://quotes.toscrape.com/js/

Обычный requests не работает, потому что цитаты подгружаются через JavaScript. Используй Playwright.

Требования:
1. Использовать Chrome WebDriver
2. Настроить браузер в headless-режиме (без графического интерфейса)
3. Использовать явные ожидания (WebDriverWait) для загрузки цитат
4. Собрать все цитаты с первой страницы: текст, автор, теги
5. Реализовать переход по страницам (клик по кнопке "Next")
6. Собрать данные со всех доступных страниц
7. Сохранить результат в CSV
8. Добавить обработку ситуации, когда кнопка "Next" становится неактивной или исчезает

Важно: между кликами по кнопкам добавлять небольшую задержку
```
'''

import asyncio
import csv
import logging
import os
import sys
from typing import List, Dict, Optional
import platform

# Важно: импортируем правильную политику для Windows ДО создания цикла
if sys.platform == 'win32':
    # Используем ProactorEventLoop для подпроцессов в Windows
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError

# --- Настройка логирования ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# --- Константы ---
TARGET_URL = "http://quotes.toscrape.com/js/"
OUTPUT_CSV_FILE = "quotes_with_playwright.csv"
HEADLESS_MODE = True
PAGE_LOAD_TIMEOUT = 60000  # Увеличил таймаут для Windows
ELEMENT_TIMEOUT = 15000
CLICK_DELAY = 2  # Увеличил задержку для надежности
MAX_RETRIES = 3

# Путь к исполняемому файлу Chromium (можно указать вручную, если нужно)
CHROMIUM_PATH = None  # Если None, Playwright найдет сам


class QuoteScraper:
    """Класс для сбора цитат с динамического сайта с помощью Playwright."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.all_quotes: List[Dict[str, str]] = []
        self._closed = False
        self._context = None

    async def __aenter__(self):
        """Асинхронный контекстный менеджер для инициализации браузера."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный контекстный менеджер для закрытия браузера."""
        await self.cleanup()

    async def start(self):
        """Инициализация Playwright и браузера с дополнительными настройками для Windows."""
        try:
            logger.info("🔄 Запуск Playwright...")

            # Запускаем Playwright
            self.playwright = await async_playwright().start()

            # Опции запуска браузера
            launch_options = {
                'headless': self.headless,
                'args': [
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-dev-shm-usage',  # Важно для Windows
                    '--disable-gpu',  # Отключаем GPU для совместимости
                ]
            }

            # Добавляем путь к Chromium, если указан
            if CHROMIUM_PATH:
                launch_options['executable_path'] = CHROMIUM_PATH

            logger.info(f"🚀 Запуск браузера в {'headless' if self.headless else 'обычном'} режиме...")

            # Запускаем браузер
            self.browser = await self.playwright.chromium.launch(**launch_options)

            # Создаем контекст с увеличенными таймаутами
            self._context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                ignore_https_errors=True  # Игнорируем ошибки HTTPS
            )

            self.page = await self._context.new_page()

            # Устанавливаем таймауты
            self.page.set_default_timeout(ELEMENT_TIMEOUT)

            logger.info("✅ Браузер успешно запущен")

        except Exception as e:
            logger.error(f"❌ Ошибка при запуске браузера: {e}")
            logger.error(f"Тип ошибки: {type(e).__name__}")
            import traceback
            logger.error(f"Детали: {traceback.format_exc()}")
            await self.cleanup()
            raise

    async def cleanup(self):
        """Корректное закрытие всех ресурсов."""
        if self._closed:
            return

        logger.info("🛑 Начинаем закрытие ресурсов...")

        # Закрываем страницу
        if self.page:
            try:
                await self.page.close()
                logger.debug("✓ Страница закрыта")
            except Exception as e:
                logger.debug(f"Ошибка при закрытии страницы: {e}")
            finally:
                self.page = None

        # Закрываем контекст
        if self._context:
            try:
                await self._context.close()
                logger.debug("✓ Контекст закрыт")
            except Exception as e:
                logger.debug(f"Ошибка при закрытии контекста: {e}")
            finally:
                self._context = None

        # Закрываем браузер
        if self.browser:
            try:
                await self.browser.close()
                logger.debug("✓ Браузер закрыт")
            except Exception as e:
                logger.debug(f"Ошибка при закрытии браузера: {e}")
            finally:
                self.browser = None

        # Останавливаем Playwright
        if self.playwright:
            try:
                await self.playwright.stop()
                logger.debug("✓ Playwright остановлен")
            except Exception as e:
                logger.debug(f"Ошибка при остановке Playwright: {e}")
            finally:
                self.playwright = None

        self._closed = True
        logger.info("✅ Все ресурсы закрыты")

    async def navigate_to_first_page(self):
        """Переходит на целевую страницу и ждет загрузки основного контента."""
        if not self.page:
            raise RuntimeError("Браузер не инициализирован")

        logger.info(f"🌐 Переходим на страницу: {TARGET_URL}")

        for attempt in range(MAX_RETRIES):
            try:
                # Используем wait_until="commit" для более быстрой загрузки
                response = await self.page.goto(
                    TARGET_URL,
                    timeout=PAGE_LOAD_TIMEOUT,
                    wait_until="commit"
                )

                if response and not response.ok:
                    logger.warning(f"⚠️ Статус ответа: {response.status}")

                # Ждем появления контента
                await self.page.wait_for_selector('.quote', timeout=ELEMENT_TIMEOUT)

                # Дополнительная задержка для загрузки JavaScript
                await asyncio.sleep(2)

                logger.info("✅ Страница загружена, цитаты найдены")
                return

            except PlaywrightTimeoutError as e:
                logger.warning(f"⚠️ Попытка {attempt + 1}/{MAX_RETRIES}: Таймаут при загрузке")
                if attempt == MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(3)
            except Exception as e:
                logger.error(f"❌ Ошибка при загрузке: {e}")
                if attempt == MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(3)

    async def parse_current_page(self) -> List[Dict[str, str]]:
        """
        Собирает цитаты с текущей страницы.
        """
        if not self.page:
            raise RuntimeError("Браузер не инициализирован")

        quotes_on_page = []

        try:
            # Ждем загрузки цитат
            await self.page.wait_for_selector('.quote', timeout=ELEMENT_TIMEOUT)

            # Находим все элементы цитат
            quote_elements = await self.page.query_selector_all('.quote')
            logger.info(f"📄 Найдено цитат на странице: {len(quote_elements)}")

            for i, quote_element in enumerate(quote_elements, 1):
                try:
                    # Текст цитаты
                    text_element = await quote_element.query_selector('.text')
                    text = await text_element.inner_text() if text_element else ""

                    # Автор цитаты
                    author_element = await quote_element.query_selector('.author')
                    author = await author_element.inner_text() if author_element else ""

                    # Теги
                    tags = []
                    tag_elements = await quote_element.query_selector_all('.tags .tag')
                    for tag_element in tag_elements:
                        tag_text = await tag_element.inner_text()
                        tags.append(tag_text)

                    quotes_on_page.append({
                        'text': text,
                        'author': author,
                        'tags': ', '.join(tags)
                    })

                    if i % 5 == 0:  # Логируем каждую 5-ю цитату
                        logger.debug(f"  ✓ Обработано {i} цитат")

                except Exception as e:
                    logger.warning(f"Ошибка при парсинге цитаты {i}: {e}")

        except Exception as e:
            logger.error(f"Ошибка при парсинге страницы: {e}")

        return quotes_on_page

    async def has_next_button(self) -> bool:
        """
        Проверяет, активна ли кнопка 'Next'.
        """
        if not self.page:
            raise RuntimeError("Браузер не инициализирован")

        try:
            # Ждем появления кнопки
            next_button = await self.page.wait_for_selector('li.next > a', timeout=5000)

            if not next_button:
                return False

            # Проверяем видимость
            is_visible = await next_button.is_visible()
            if not is_visible:
                return False

            # Проверяем, не заблокирована ли кнопка
            parent_li = await next_button.evaluate_handle('(element) => element.closest("li")')
            is_disabled = await parent_li.evaluate('(li) => li.classList.contains("disabled")')

            return not is_disabled

        except PlaywrightTimeoutError:
            logger.debug("Кнопка Next не найдена на странице")
            return False
        except Exception as e:
            logger.error(f"Ошибка при проверке кнопки Next: {e}")
            return False

    async def click_next(self):
        """Кликает по кнопке 'Next'."""
        if not self.page:
            raise RuntimeError("Браузер не инициализирован")

        try:
            # Прокручиваем к кнопке для уверенности
            next_button = await self.page.query_selector('li.next a')
            if next_button:
                await next_button.scroll_into_view_if_needed()
                await asyncio.sleep(0.5)

                # Кликаем
                await next_button.click()

                # Ждем загрузки новых цитат
                await self.page.wait_for_selector('.quote', timeout=ELEMENT_TIMEOUT)

                # Дополнительная задержка
                await asyncio.sleep(CLICK_DELAY)

                logger.info("✅ Перешли на следующую страницу")
            else:
                logger.warning("❌ Кнопка Next не найдена для клика")

        except Exception as e:
            logger.error(f"❌ Ошибка при клике по кнопке Next: {e}")
            raise

    async def scrape_all_pages(self):
        """Основной метод для обхода всех страниц."""
        if not self.page:
            raise RuntimeError("Браузер не инициализирован")

        await self.navigate_to_first_page()

        page_number = 1
        retry_count = 0
        max_page_retries = 3

        while True:
            try:
                logger.info(f"📖 Обрабатываем страницу {page_number}...")

                page_quotes = await self.parse_current_page()
                self.all_quotes.extend(page_quotes)

                logger.info(f"✅ Страница {page_number}: собрано {len(page_quotes)} цитат")

                retry_count = 0

                if await self.has_next_button():
                    await self.click_next()
                    page_number += 1
                else:
                    logger.info(f"🏁 Достигнута последняя страница. Всего обработано: {page_number}")
                    break

            except Exception as e:
                retry_count += 1
                logger.error(f"❌ Ошибка на странице {page_number}: {e}")

                if retry_count >= max_page_retries:
                    logger.error(f"⚠️ Достигнут лимит попыток. Прерываем сбор.")
                    break

                logger.info(f"🔄 Повторная попытка ({retry_count}/{max_page_retries})...")
                await asyncio.sleep(5)

        logger.info(f"📚 Всего собрано цитат: {len(self.all_quotes)}")

    def save_to_csv(self, filename: str):
        """Сохраняет данные в CSV."""
        if not self.all_quotes:
            logger.warning("Нет данных для сохранения.")
            return

        filepath = os.path.join(os.getcwd(), filename)
        try:
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = ['text', 'author', 'tags']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
                writer.writeheader()
                writer.writerows(self.all_quotes)
            logger.info(f"💾 Данные сохранены в: {filepath}")
        except Exception as e:
            logger.error(f"❌ Ошибка при сохранении: {e}")


async def main():
    """Главная функция."""
    logger.info("=" * 60)
    logger.info("🚀 ЗАПУСК ПАРСЕРА ЦИТАТ")
    logger.info(f"💻 Платформа: {platform.system()} {platform.release()}")
    logger.info("=" * 60)

    scraper = None

    try:
        # Создаем скрапер
        scraper = QuoteScraper(headless=HEADLESS_MODE)

        # Запускаем
        await scraper.start()

        # Собираем данные
        await scraper.scrape_all_pages()

        # Сохраняем
        if scraper.all_quotes:
            scraper.save_to_csv(OUTPUT_CSV_FILE)
        else:
            logger.warning("⚠️ Нет данных для сохранения")

    except KeyboardInterrupt:
        logger.info("👋 Получен сигнал прерывания")
    except Exception as e:
        logger.exception(f"❌ Критическая ошибка: {e}")
    finally:
        # Закрываем ресурсы
        if scraper:
            await scraper.cleanup()

        # Даем время на закрытие
        await asyncio.sleep(0.5)

    logger.info("=" * 60)
    logger.info("🏁 РАБОТА ПРОГРАММЫ ЗАВЕРШЕНА")
    logger.info("=" * 60)


def run_main():
    """Функция запуска с правильной настройкой для Windows."""
    if sys.platform == 'win32':
        # Используем ProactorEventLoop для Windows
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
    else:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("👋 Программа завершена пользователем")
    except Exception as e:
        logger.exception(f"❌ Необработанная ошибка: {e}")
    finally:
        # Закрываем все незавершенные задачи
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()

        # Даем время на отмену задач
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

        loop.close()


if __name__ == "__main__":
    run_main()