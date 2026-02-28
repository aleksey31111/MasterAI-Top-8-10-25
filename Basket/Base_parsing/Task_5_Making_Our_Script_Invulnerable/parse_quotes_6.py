import requests
from bs4 import BeautifulSoup
import time
from tqdm import tqdm
import json
import logging
from urllib.parse import urljoin
import signal
import sys
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import hashlib


class RobustQuoteScraper:
    """
    Профессиональный парсер с обработкой ошибок и логированием
    """

    def __init__(self, base_url="http://quotes.toscrape.com"):
        self.base_url = base_url
        self.all_quotes = []
        self.quotes_set = set()
        self.pages_content = []
        self.interrupted = False

        # Настройка логирования
        self.setup_logging()

        # Настройка сессии с повторными попытками
        self.setup_session()

        # Настройка обработчика прерывания
        signal.signal(signal.SIGINT, self.signal_handler)

    def setup_logging(self):
        """
        Настройка логирования в файл и консоль
        """
        # Создаём имя файла лога с датой
        log_filename = f'scraper_{datetime.now().strftime("%Y%m%d")}.log'

        # Настройка формата логирования
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler()  # Вывод в консоль
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("🚀 Парсер инициализирован")

    def setup_session(self):
        """
        Настройка HTTP сессии с повторными попытками
        """
        self.session = requests.Session()

        # Настройка стратегии повторных попыток
        retry_strategy = Retry(
            total=3,  # Максимум 3 попытки
            backoff_factor=1,  # Задержка между попытками: 1, 2, 4 секунды
            status_forcelist=[429, 500, 502, 503, 504],  # Коды для повторных попыток
            allowed_methods=["GET"]  # Только для GET запросов
        )

        # Создаём адаптер с нашей стратегией
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10
        )

        # Применяем адаптер к сессии
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Устанавливаем заголовки
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        })

    def signal_handler(self, signum, frame):
        """
        Обработка сигнала прерывания (Ctrl+C)
        """
        self.logger.warning("⚠️ Получен сигнал прерывания. Завершаем работу...")
        self.interrupted = True

    def validate_quote(self, quote_data):
        """
        Валидация данных цитаты
        """
        # Проверка наличия обязательных полей
        if not quote_data.get('text'):
            self.logger.warning("Цитата без текста пропущена")
            return False

        # Проверка длины цитаты (разумные границы)
        if len(quote_data['text']) < 5 or len(quote_data['text']) > 500:
            self.logger.warning(f"Цитата с подозрительной длиной: {len(quote_data['text'])} символов")
            return False

        # Проверка автора
        if not quote_data.get('author'):
            self.logger.warning("Цитата без автора пропущена")
            return False

        # Проверка на битые символы
        try:
            quote_data['text'].encode('utf-8').decode('utf-8')
        except UnicodeError:
            self.logger.error("Цитата содержит некорректные символы")
            return False

        return True

    def safe_request(self, url, timeout=10):
        """
        Безопасный запрос с обработкой всех возможных ошибок
        """
        try:
            self.logger.debug(f"Запрос к {url}")
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()  # Проверка HTTP статуса
            return response

        except requests.exceptions.Timeout:
            self.logger.error(f"Таймаут при запросе к {url}")
            raise

        except requests.exceptions.ConnectionError:
            self.logger.error(f"Ошибка соединения с {url}")
            raise

        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP ошибка {e.response.status_code} для {url}")
            raise

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Неизвестная ошибка запроса: {e}")
            raise

    def fetch_all_pages(self):
        """
        Сбор всех страниц с обработкой ошибок
        """
        current_url = self.base_url
        page_num = 1
        max_retries = 3

        self.logger.info("🔍 Начинаем обход страниц...")

        while current_url and not self.interrupted:
            for attempt in range(max_retries):
                try:
                    # Задержка между страницами
                    if page_num > 1:
                        time.sleep(1)  # Базовая задержка

                    response = self.safe_request(current_url)

                    # Парсим страницу
                    soup = BeautifulSoup(response.text, 'html.parser')

                    self.pages_content.append({
                        'number': page_num,
                        'url': current_url,
                        'soup': soup,
                        'timestamp': datetime.now().isoformat()
                    })

                    self.logger.info(f"✅ Страница {page_num} загружена (попытка {attempt + 1})")

                    # Ищем следующую страницу
                    next_li = soup.find('li', class_='next')
                    if next_li and next_li.find('a'):
                        next_link = next_li.find('a').get('href')
                        current_url = urljoin(self.base_url, next_link)
                        page_num += 1
                        break  # Успешно, выходим из цикла повторных попыток
                    else:
                        self.logger.info(f"🏁 Достигнута последняя страница. Всего: {page_num}")
                        current_url = None
                        break

                except requests.exceptions.Timeout:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # Экспоненциальная задержка
                        self.logger.warning(f"⏳ Таймаут. Повтор через {wait_time}с...")
                        time.sleep(wait_time)
                    else:
                        self.logger.error(f"❌ Не удалось загрузить страницу {page_num} после {max_retries} попыток")
                        current_url = None

                except Exception as e:
                    self.logger.error(f"❌ Критическая ошибка на странице {page_num}: {e}")
                    current_url = None
                    break

            if self.interrupted:
                self.logger.warning("🛑 Обход страниц прерван пользователем")
                break

    def process_quotes(self):
        """
        Обработка всех собранных страниц с валидацией
        """
        if not self.pages_content:
            self.logger.error("Нет страниц для обработки")
            return []

        self.logger.info(f"🔄 Начинаем обработку {len(self.pages_content)} страниц...")

        # Создаём прогресс-бар с логированием
        pbar = tqdm(
            self.pages_content,
            desc="Обработка страниц",
            unit="стр",
            position=0,
            leave=True
        )

        quotes_found = 0
        quotes_valid = 0
        quotes_duplicate = 0

        for page_data in pbar:
            if self.interrupted:
                self.logger.warning("🛑 Обработка прервана пользователем")
                break

            soup = page_data['soup']
            quotes_on_page = soup.find_all('div', class_='quote')

            pbar.set_description(f"Стр {page_data['number']} (найдено: {quotes_found})")

            for quote in quotes_on_page:
                try:
                    # Извлекаем данные с проверкой на None
                    text_elem = quote.find('span', class_='text')
                    author_elem = quote.find('small', class_='author')
                    tag_elems = quote.find_all('a', class_='tag')

                    # Пропускаем, если не удалось извлечь текст
                    if not text_elem:
                        self.logger.debug("Пропущен элемент без текста цитаты")
                        continue

                    quote_text = text_elem.text.strip()
                    quotes_found += 1

                    # Проверка на уникальность (используем хеш для эффективности)
                    quote_hash = hashlib.md5(quote_text.encode('utf-8')).hexdigest()
                    if quote_hash in self.quotes_set:
                        quotes_duplicate += 1
                        continue

                    # Извлекаем остальные данные
                    author = author_elem.text.strip() if author_elem else "Unknown"
                    tags = [tag.text for tag in tag_elems] if tag_elems else []

                    # Создаём объект цитаты
                    quote_data = {
                        'text': quote_text,
                        'author': author,
                        'tags': tags,
                        'page': page_data['number'],
                        'hash': quote_hash,
                        'timestamp': datetime.now().isoformat()
                    }

                    # Валидация
                    if self.validate_quote(quote_data):
                        self.all_quotes.append(quote_data)
                        self.quotes_set.add(quote_hash)
                        quotes_valid += 1
                    else:
                        self.logger.warning(f"❌ Невалидная цитата на стр. {page_data['number']}")

                except Exception as e:
                    self.logger.error(f"Ошибка при обработке цитаты: {e}")

        # Логируем статистику обработки
        self.logger.info(
            f"📊 Статистика: найдено {quotes_found}, уникальных {quotes_valid}, дубликатов {quotes_duplicate}")

        return self.all_quotes

    def save_checkpoint(self):
        """
        Сохранение промежуточных результатов
        """
        if self.all_quotes:
            checkpoint_file = f"checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'quotes': self.all_quotes,
                    'pages_processed': len(self.pages_content),
                    'timestamp': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            self.logger.info(f"💾 Чекпоинт сохранён: {checkpoint_file}")

    def run(self):
        """
        Основной метод запуска
        """
        self.logger.info("=" * 60)
        self.logger.info("🚀 ЗАПУСК ПРОФЕССИОНАЛЬНОГО ПАРСЕРА")
        self.logger.info("=" * 60)

        start_time = time.time()

        try:
            # Этап 1: Сбор страниц
            self.fetch_all_pages()

            if self.interrupted:
                self.save_checkpoint()
                return

            # Этап 2: Обработка цитат
            quotes = self.process_quotes()

            if self.interrupted:
                self.save_checkpoint()
                return

            # Этап 3: Сохранение результатов
            if quotes:
                self.save_results(quotes)
                self.print_statistics(quotes, time.time() - start_time)
            else:
                self.logger.error("❌ Не удалось собрать цитаты")

        except Exception as e:
            self.logger.error(f"💥 Критическая ошибка: {e}", exc_info=True)
            self.save_checkpoint()

        finally:
            self.logger.info("👋 Парсер завершил работу")

    def save_results(self, quotes, format='json'):
        """
        Сохранение результатов с резервным копированием
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Основной файл
        filename = f"quotes_complete_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'total_quotes': len(quotes),
                    'pages': len(self.pages_content),
                    'timestamp': timestamp,
                    'source': self.base_url
                },
                'quotes': quotes
            }, f, ensure_ascii=False, indent=2)

        self.logger.info(f"💾 Сохранено {len(quotes)} цитат в {filename}")

        # Сохраняем также в читаемом формате
        txt_filename = f"quotes_readable_{timestamp}.txt"
        with open(txt_filename, 'w', encoding='utf-8') as f:
            for i, quote in enumerate(quotes, 1):
                f.write(f"Цитата #{i} (стр. {quote['page']})\n")
                f.write(f"\"{quote['text']}\"\n")
                f.write(f"— {quote['author']}\n")
                if quote['tags']:
                    f.write(f"Теги: {', '.join(quote['tags'])}\n")
                f.write("-" * 60 + "\n")

        self.logger.info(f"💾 Читаемая версия: {txt_filename}")

    def print_statistics(self, quotes, elapsed_time):
        """
        Детальная статистика сбора
        """
        self.logger.info("=" * 60)
        self.logger.info("📊 ИТОГОВАЯ СТАТИСТИКА")
        self.logger.info("=" * 60)

        self.logger.info(f"⏱️  Время выполнения: {elapsed_time:.1f} секунд")
        self.logger.info(f"📄 Страниц обработано: {len(self.pages_content)}")
        self.logger.info(f"💬 Всего цитат: {len(quotes)}")

        # Статистика по авторам
        from collections import Counter
        authors = [q['author'] for q in quotes]
        author_counts = Counter(authors)

        self.logger.info("🏆 Топ-5 авторов:")
        for author, count in author_counts.most_common(5):
            self.logger.info(f"   • {author}: {count}")

        # Статистика по тегам
        all_tags = []
        for q in quotes:
            all_tags.extend(q['tags'])
        tag_counts = Counter(all_tags)

        self.logger.info("🏷️  Топ-5 тегов:")
        for tag, count in tag_counts.most_common(5):
            self.logger.info(f"   • #{tag}: {count}")

        self.logger.info("=" * 60)


def main():
    """
    Точка входа
    """
    scraper = RobustQuoteScraper()

    try:
        scraper.run()
    except KeyboardInterrupt:
        scraper.logger.info("👋 Программа остановлена пользователем")
        scraper.save_checkpoint()
    except Exception as e:
        scraper.logger.error(f"💥 Непредвиденная ошибка: {e}")
        scraper.save_checkpoint()


if __name__ == "__main__":
    main()