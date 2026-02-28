import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin
import os


def fetch_page_quotes(url):
    """
    Извлекает цитаты со страницы.

    Args:
        url (str): URL страницы с цитатами

    Returns:
        tuple: (список цитат, URL следующей страницы или None)
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Ошибка при загрузке страницы {url}: {e}")
        return [], None

    soup = BeautifulSoup(response.text, 'html.parser')
    quotes = []

    # Поиск всех цитат на странице (пример для сайта quotes.toscrape.com)
    quote_elements = soup.find_all('div', class_='quote')

    for quote in quote_elements:
        try:
            text = quote.find('span', class_='text').text
            author = quote.find('small', class_='author').text

            # Извлечение тегов
            tag_elements = quote.find_all('a', class_='tag')
            tags = [tag.text for tag in tag_elements]

            quotes.append({
                'text': text,
                'author': author,
                'tags': tags
            })
        except AttributeError as e:
            print(f"Ошибка при парсинге цитаты: {e}")
            continue

    # Поиск ссылки на следующую страницу
    next_button = soup.find('li', class_='next')
    next_url = None
    if next_button and next_button.find('a'):
        next_url = urljoin(url, next_button.find('a')['href'])

    return quotes, next_url


def save_quotes_to_file(quotes, filename='quotes.txt'):
    """
    Сохраняет цитаты в текстовый файл.

    Args:
        quotes (list): Список словарей с цитатами
        filename (str): Имя файла для сохранения

    Returns:
        bool: True если сохранение успешно, иначе False
    """
    try:
        # Проверяем, существует ли файл, и выбираем режим записи
        mode = 'w' if not os.path.exists(filename) else 'a'

        with open(filename, mode, encoding='utf-8') as file:
            for i, quote in enumerate(quotes, 1):
                # Форматируем теги
                tags_str = ', '.join(quote['tags']) if quote['tags'] else 'нет тегов'

                # Записываем цитату в требуемом формате
                file.write(f"===== ЦИТАТА {i} =====\n")
                file.write(f'Текст: "{quote["text"]}"\n')
                file.write(f"Автор: {quote['author']}\n")
                file.write(f"Теги: {tags_str}\n\n")

        return True
    except PermissionError:
        print(f"Ошибка: нет прав на запись в файл {filename}")
        return False
    except IOError as e:
        print(f"Ошибка ввода-вывода при работе с файлом {filename}: {e}")
        return False
    except Exception as e:
        print(f"Неожиданная ошибка при сохранении в файл: {e}")
        return False


def scrape_quotes(base_url, delay=1):
    """
    Основная функция для сбора цитат со всех страниц.

    Args:
        base_url (str): Начальный URL для парсинга
        delay (int): Задержка между запросами в секундах

    Returns:
        list: Все собранные цитаты
    """
    all_quotes = []
    current_url = base_url
    page_num = 1

    print("Начинаем сбор цитат...")

    while current_url:
        print(f"Обрабатывается страница {page_num}: {current_url}")

        quotes, next_url = fetch_page_quotes(current_url)

        if quotes:
            print(f"  Найдено цитат на странице: {len(quotes)}")
            all_quotes.extend(quotes)
        else:
            print(f"  Цитат не найдено на странице {page_num}")

        current_url = next_url
        page_num += 1

        if current_url and delay > 0:
            print(f"  Ожидание {delay} секунд перед следующим запросом...")
            time.sleep(delay)

    return all_quotes


def main():
    """Главная функция программы."""
    # Настройки
    START_URL = "http://quotes.toscrape.com"
    REQUEST_DELAY = 1  # Задержка между запросами в секундах
    OUTPUT_FILE = "quotes.txt"

    print("=" * 50)
    print("ПАРСЕР ЦИТАТ")
    print("=" * 50)

    try:
        # Сбор цитат
        all_quotes = scrape_quotes(START_URL, REQUEST_DELAY)

        print("\n" + "=" * 50)
        print(f"Всего собрано цитат: {len(all_quotes)}")

        if all_quotes:
            # Сохранение в файл
            print(f"\nСохраняем цитаты в файл '{OUTPUT_FILE}'...")

            if save_quotes_to_file(all_quotes, OUTPUT_FILE):
                print(f"✅ Успешно сохранено {len(all_quotes)} цитат в файл {OUTPUT_FILE}")

                # Показываем пример сохраненных данных
                print("\nПример сохраненной цитаты:")
                example = all_quotes[0]
                print(f'  Текст: "{example["text"][:50]}..."')
                print(f"  Автор: {example['author']}")
                print(f"  Теги: {', '.join(example['tags'])}")
            else:
                print("❌ Не удалось сохранить цитаты в файл")
        else:
            print("❌ Не удалось собрать цитаты")

    except KeyboardInterrupt:
        print("\n\nПрограмма остановлена пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")

    print("\nРабота программы завершена")


if __name__ == "__main__":
    main()