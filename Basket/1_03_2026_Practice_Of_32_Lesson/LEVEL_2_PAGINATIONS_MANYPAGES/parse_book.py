import requests
from bs4 import BeautifulSoup
import csv
import time
from tqdm import tqdm  # Библиотека для прогресс-бара
import os


def parse_all_books(base_url="http://books.toscrape.com/catalogue/page-1.html"):
    """
    Парсит все книги со всех страниц каталога books.toscrape.com
    """

    # Заголовки для имитации браузера
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    all_books = []  # Список для всех книг
    current_page = 1
    total_pages = None

    print("🔍 Начинаем сбор книг с сайта...")
    print("=" * 60)

    # Сначала узнаем общее количество страниц
    try:
        first_response = requests.get(base_url, headers=headers, timeout=10)
        first_response.raise_for_status()
        first_soup = BeautifulSoup(first_response.text, 'html.parser')

        # Ищем информацию о пагинации
        pagination = first_soup.find('li', class_='current')
        if pagination:
            # Текст обычно вида "Page 1 of 50"
            total_pages = int(pagination.text.strip().split()[-1])
            print(f"📚 Всего страниц в каталоге: {total_pages}")
        else:
            # Если не нашли пагинацию, будем собирать, пока есть кнопка "next"
            print("📚 Точное число страниц неизвестно, будем собирать до последней")

    except Exception as e:
        print(f"⚠️ Не удалось определить общее число страниц: {e}")

    print("=" * 60)

    # Основной цикл сбора книг
    with tqdm(desc="Сбор книг", unit=" стр") as pbar:
        while True:
            # Формируем URL текущей страницы
            if current_page == 1:
                url = base_url
            else:
                url = f"http://books.toscrape.com/catalogue/page-{current_page}.html"

            try:
                # Отправляем запрос
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()

                # Парсим страницу
                soup = BeautifulSoup(response.text, 'html.parser')

                # Находим все книги на странице
                books = soup.find_all('article', class_='product_pod')

                if not books:
                    print(f"\n⚠️ На странице {current_page} не найдено книг. Завершаем сбор.")
                    break

                # Извлекаем информацию о каждой книге
                for book in books:
                    # Название книги
                    title_tag = book.find('h3').find('a')
                    title = title_tag.get('title', '') or title_tag.text.strip()

                    # Цена
                    price_tag = book.find('p', class_='price_color')
                    price = price_tag.text.strip() if price_tag else 'N/A'

                    # Наличие (в stock/out of stock)
                    stock_tag = book.find('p', class_='instock availability')
                    stock = 'In stock' if stock_tag and 'In stock' in stock_tag.text else 'Out of stock'

                    # Рейтинг (класс содержит rating, например, "star-rating Three")
                    rating_tag = book.find('p', class_='star-rating')
                    rating = 'No rating'
                    if rating_tag:
                        # Извлекаем второй класс (например, "Three" из "star-rating Three")
                        classes = rating_tag.get('class', [])
                        if len(classes) > 1:
                            rating = classes[1]

                    # Ссылка на книгу
                    relative_link = title_tag.get('href', '')
                    if relative_link.startswith('catalogue/'):
                        book_link = f"http://books.toscrape.com/{relative_link}"
                    else:
                        book_link = f"http://books.toscrape.com/catalogue/{relative_link}"

                    all_books.append({
                        'title': title,
                        'price': price,
                        'availability': stock,
                        'rating': rating,
                        'url': book_link,
                        'page': current_page
                    })

                # Обновляем прогресс-бар
                pbar.update(1)
                pbar.set_postfix({'Книг на стр': len(books), 'Всего книг': len(all_books)})

                # Проверяем, есть ли следующая страница
                next_button = soup.find('li', class_='next')
                if not next_button:
                    print(f"\n✅ Достигнута последняя страница ({current_page})")
                    break

                # Вежливая задержка между запросами
                time.sleep(1)

                current_page += 1

                # Если мы знаем общее количество страниц, обновляем описание прогресс-бара
                if total_pages:
                    pbar.total = total_pages

            except requests.exceptions.RequestException as e:
                print(f"\n❌ Ошибка при загрузке страницы {current_page}: {e}")
                break
            except Exception as e:
                print(f"\n❌ Неожиданная ошибка на странице {current_page}: {e}")
                break

    return all_books


def save_to_csv(books, filename='all_books.csv'):
    """
    Сохраняет все книги в CSV файл
    """
    if not books:
        print("❌ Нет данных для сохранения")
        return

    # Поля для CSV
    fieldnames = ['title', 'price', 'availability', 'rating', 'url', 'page']

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(books)

        print(f"\n💾 Данные сохранены в файл: {filename}")
        print(f"   Размер файла: {os.path.getsize(filename)} байт")

    except Exception as e:
        print(f"❌ Ошибка при сохранении CSV: {e}")


def calculate_statistics(books):
    """
    Вычисляет и выводит статистику по собранным книгам
    """
    if not books:
        return

    print("\n" + "=" * 60)
    print("📊 СТАТИСТИКА СБОРА")
    print("=" * 60)

    # Общее количество книг
    total_books = len(books)
    print(f"📚 Всего книг собрано: {total_books}")

    # Количество страниц
    pages = set(book['page'] for book in books)
    print(f"📄 Всего страниц обработано: {len(pages)}")

    # Книги в наличии и отсутствующие
    in_stock = sum(1 for book in books if book['availability'] == 'In stock')
    out_of_stock = total_books - in_stock
    print(f"✅ В наличии: {in_stock} книг ({in_stock / total_books * 100:.1f}%)")
    print(f"❌ Отсутствуют: {out_of_stock} книг ({out_of_stock / total_books * 100:.1f}%)")

    # Распределение по рейтингу
    ratings = {}
    for book in books:
        rating = book['rating']
        ratings[rating] = ratings.get(rating, 0) + 1

    print("\n⭐ Распределение по рейтингу:")
    for rating in ['One', 'Two', 'Three', 'Four', 'Five', 'No rating']:
        count = ratings.get(rating, 0)
        percentage = count / total_books * 100 if total_books > 0 else 0
        print(f"   {rating}: {count} книг ({percentage:.1f}%)")

    # Статистика по ценам
    prices = []
    for book in books:
        try:
            # Очищаем цену от символа £ и преобразуем в число
            price_str = book['price'].replace('£', '').replace('Â', '')
            price = float(price_str)
            prices.append(price)
        except (ValueError, AttributeError):
            continue

    if prices:
        print(f"\n💰 Статистика цен (в £):")
        print(f"   Средняя цена: {sum(prices) / len(prices):.2f}")
        print(f"   Минимальная цена: {min(prices):.2f}")
        print(f"   Максимальная цена: {max(prices):.2f}")
        print(f"   Медианная цена: {sorted(prices)[len(prices) // 2]:.2f}")

    # Топ-5 самых дорогих книг
    if prices:
        print("\n🏆 Топ-5 самых дорогих книг:")
        books_with_price = [(book, float(book['price'].replace('£', '').replace('Â', '')))
                            for book in books if book['price'] != 'N/A']
        top_expensive = sorted(books_with_price, key=lambda x: x[1], reverse=True)[:5]
        for i, (book, price) in enumerate(top_expensive, 1):
            print(f"   {i}. {book['title'][:50]}... - £{price:.2f}")

    print("=" * 60)


def main():
    """
    Основная функция программы
    """
    print("🐍 ПАРСЕР КНИГ С BOOKS.TOSCRAPE.COM")
    print("=" * 60)

    # Начальный URL
    start_url = "http://books.toscrape.com/catalogue/page-1.html"

    # Собираем все книги
    all_books = parse_all_books(start_url)

    # Сохраняем в CSV
    save_to_csv(all_books)

    # Выводим статистику
    calculate_statistics(all_books)

    print("\n✅ Программа завершена успешно!")


if __name__ == "__main__":
    main()