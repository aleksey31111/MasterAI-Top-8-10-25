import requests
from bs4 import BeautifulSoup
import time
from tqdm import tqdm  # для прогресс-бара
import json
import os
from urllib.parse import urljoin  # для правильного формирования URL


def get_all_quotes(base_url="http://quotes.toscrape.com"):
    """
    Функция для сбора всех цитат со всех страниц сайта
    """
    all_quotes = []  # Здесь будут все собранные цитаты
    current_url = base_url
    page_num = 1
    quotes_set = set()  # Множество для проверки уникальности цитат

    # Создаём прогресс-бар, но его длину мы пока не знаем
    # Поэтому сначала будем собирать страницы, а потом покажем прогресс
    pages_content = []

    print("🔍 Начинаем обход страниц...")

    # ПЕРВЫЙ ЭТАП: Собираем все страницы
    while current_url:
        try:
            # Вежливая задержка перед запросом (кроме первой страницы)
            if page_num > 1:
                time.sleep(1)  # Спим секунду, чтобы не нагружать сервер

            # Отправляем запрос с заголовком, имитирующим браузер
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(current_url, headers=headers)

            if response.status_code != 200:
                print(f"❌ Ошибка на странице {page_num}: {response.status_code}")
                break

            # Парсим страницу
            soup = BeautifulSoup(response.text, 'html.parser')

            # Сохраняем информацию о странице
            pages_content.append({
                'number': page_num,
                'url': current_url,
                'soup': soup
            })

            print(f"  📄 Страница {page_num} загружена")

            # *** ИЩЕМ ССЫЛКУ НА СЛЕДУЮЩУЮ СТРАНИЦУ ***
            # Ищем элемент <li class="next"> с ссылкой внутри
            next_li = soup.find('li', class_='next')

            if next_li and next_li.find('a'):
                # Находим относительную ссылку (например, "/page/2/")
                next_link = next_li.find('a').get('href')
                # Преобразуем относительную ссылку в абсолютную
                current_url = urljoin(base_url, next_link)
                page_num += 1
            else:
                # Если нет кнопки "Next" — это последняя страница
                print(f"\n✅ Достигнута последняя страница! Всего страниц: {page_num}")
                current_url = None

        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка соединения: {e}")
            break
        except Exception as e:
            print(f"❌ Неожиданная ошибка: {e}")
            break

    # ВТОРОЙ ЭТАП: Обрабатываем все собранные страницы с прогресс-баром
    print(f"\n🔄 Начинаем обработку {len(pages_content)} страниц...\n")

    for page_data in tqdm(pages_content, desc="Обработка страниц", unit="стр"):
        soup = page_data['soup']

        # Находим все цитаты на текущей странице
        quotes_on_page = soup.find_all('div', class_='quote')

        for quote in quotes_on_page:
            # Извлекаем текст цитаты
            text_elem = quote.find('span', class_='text')
            quote_text = text_elem.text.strip() if text_elem else "Текст не найден"

            # Проверка на уникальность (текст цитаты обычно уникален)
            if quote_text in quotes_set:
                continue  # Пропускаем, если уже встречали такую цитату
            quotes_set.add(quote_text)

            # Извлекаем автора
            author_elem = quote.find('small', class_='author')
            author = author_elem.text.strip() if author_elem else "Автор не найден"

            # Извлекаем теги
            tag_elems = quote.find_all('a', class_='tag')
            tags = [tag.text for tag in tag_elems]

            # Добавляем цитату в общий список
            all_quotes.append({
                'text': quote_text,
                'author': author,
                'tags': tags,
                'page': page_data['number']
            })

    return all_quotes


def save_quotes(quotes, format='json'):
    """
    Сохраняет цитаты в файл
    """
    # Создаём имя файла с временной меткой
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    if format == 'json':
        filename = f'all_quotes_{timestamp}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            # Используем ensure_ascii=False для сохранения кавычек-ёлочек
            json.dump(quotes, f, ensure_ascii=False, indent=2)
        print(f"💾 Сохранено {len(quotes)} цитат в файл {filename}")

    elif format == 'txt':
        filename = f'all_quotes_{timestamp}.txt'
        with open(filename, 'w', encoding='utf-8') as f:
            for i, quote in enumerate(quotes, 1):
                f.write(f"Цитата #{i} (стр. {quote['page']})\n")
                f.write(f"Текст: {quote['text']}\n")
                f.write(f"Автор: {quote['author']}\n")
                f.write(f"Теги: {', '.join(quote['tags'])}\n")
                f.write("=" * 70 + "\n\n")
        print(f"💾 Сохранено {len(quotes)} цитат в файл {filename}")

    else:
        print("❌ Неподдерживаемый формат файла")

    return filename


def print_statistics(quotes):
    """
    Выводит статистику по собранным цитатам
    """
    print("\n" + "=" * 70)
    print("📊 СТАТИСТИКА СБОРА")
    print("=" * 70)

    # Общее количество
    print(f"Всего собрано цитат: {len(quotes)}")

    # Топ-10 авторов
    from collections import Counter
    authors = [q['author'] for q in quotes]
    author_counts = Counter(authors)

    print("\n🏆 Топ-10 авторов:")
    for author, count in author_counts.most_common(10):
        print(f"   {author}: {count} цитат")

    # Топ-10 тегов
    all_tags = []
    for q in quotes:
        all_tags.extend(q['tags'])
    tag_counts = Counter(all_tags)

    print("\n🏷️ Топ-10 тегов:")
    for tag, count in tag_counts.most_common(10):
        print(f"   #{tag}: {count} раз")

    # Количество страниц
    pages = set(q['page'] for q in quotes)
    print(f"\n📄 Страниц обработано: {len(pages)}")

    print("=" * 70)


def main():
    """
    Основная функция
    """
    print("🚀 ЗАПУСК СБОРЩИКА ЦИТАТ")
    print("=" * 70)

    # Начинаем сбор
    start_time = time.time()
    quotes = get_all_quotes()
    elapsed_time = time.time() - start_time

    if quotes:
        print(f"\n✨ Собрано {len(quotes)} цитат за {elapsed_time:.1f} секунд")

        # Сохраняем в разных форматах
        save_quotes(quotes, 'json')
        save_quotes(quotes, 'txt')

        # Выводим статистику
        print_statistics(quotes)

        # Показываем пример первых трёх цитат
        print("\n🔍 ПРИМЕРЫ СОБРАННЫХ ЦИТАТ:")
        for i, quote in enumerate(quotes[:3], 1):
            print(f"\n{i}. \"{quote['text']}\"")
            print(f"   — {quote['author']}")
    else:
        print("❌ Не удалось собрать цитаты")


if __name__ == "__main__":
    # Устанавливаем библиотеку tqdm, если её нет
    try:
        from tqdm import tqdm
    except ImportError:
        print("Устанавливаем библиотеку tqdm для прогресс-бара...")
        os.system('pip install tqdm')
        from tqdm import tqdm

    main()