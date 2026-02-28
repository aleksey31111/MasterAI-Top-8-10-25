import requests
from bs4 import BeautifulSoup
import time


def parse_quotes():
    base_url = "http://quotes.toscrape.com"
    page = 1
    all_quotes = []

    while True:
        # Формируем URL для текущей страницы
        if page == 1:
            url = base_url
        else:
            url = f"{base_url}/page/{page}/"

        print(f"Парсинг страницы {page}...")

        # Отправляем запрос с заголовками для имитации браузера
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                print(f"Страница {page} не найдена. Завершаем парсинг.")
                break

            soup = BeautifulSoup(response.text, 'lxml')

            # Находим все цитаты на странице
            quotes = soup.find_all('div', class_='quote')

            # Если цитат нет, выходим из цикла
            if not quotes:
                break

            # Извлекаем данные из каждой цитаты
            for quote in quotes:
                quote_data = {
                    'text': quote.find('span', class_='text').text,
                    'author': quote.find('small', class_='author').text,
                    'tags': [tag.text for tag in quote.find_all('a', class_='tag')]
                }
                all_quotes.append(quote_data)

            page += 1
            time.sleep(1)  # Задержка между запросами

        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе: {e}")
            break

    return all_quotes


# Сохранение результатов в файл
def save_to_file(quotes, filename='quotes.txt'):
    with open(filename, 'w', encoding='utf-8') as f:
        for i, quote in enumerate(quotes, 1):
            f.write(f"Цитата #{i}\n")
            f.write(f"Текст: {quote['text']}\n")
            f.write(f"Автор: {quote['author']}\n")
            f.write(f"Теги: {', '.join(quote['tags'])}\n")
            f.write("-" * 50 + "\n")
    print(f"Данные сохранены в файл {filename}")


# Сохранение в CSV с помощью pandas
def save_to_csv(quotes, filename='quotes.csv'):
    try:
        import pandas as pd
        df = pd.DataFrame(quotes)
        df['tags'] = df['tags'].apply(lambda x: ', '.join(x))  # Преобразуем список тегов в строку
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"Данные сохранены в файл {filename}")
    except ImportError:
        print("Библиотека pandas не установлена. Установите: pip install pandas")


# Основная программа
if __name__ == "__main__":
    print("Начинаем парсинг сайта quotes.toscrape.com...")
    quotes = parse_quotes()
    print(f"Всего собрано цитат: {len(quotes)}")

    # Сохраняем результаты
    save_to_file(quotes)
    save_to_csv(quotes)