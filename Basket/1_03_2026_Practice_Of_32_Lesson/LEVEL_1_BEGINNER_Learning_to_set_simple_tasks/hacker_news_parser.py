'''
    Промпт для ИИ:
```
Напиши Python скрипт для парсинга заголовков новостей с сайта https://news.ycombinator.com/.

Требования:
1. Используй библиотеки requests и beautifulsoup4
2. Отправь GET-запрос к сайту
3. Найди все заголовки новостей (они находятся в тегах <span class="titleline">)
4. Извлеки текст каждой ссылки
5. Сохрани заголовки в текстовый файл с нумерацией (1. Заголовок, 2. Заголовок...)
6. Добавь обработку ошибок подключения
7. Добавь комментарии к каждой строке кода

Покажи пример запуска и ожидаемый вывод.
```

'''
import requests  # Библиотека для отправки HTTP-запросов
from bs4 import BeautifulSoup  # Библиотека для парсинга HTML
import time  # Библиотека для работы с задержками


def parse_hacker_news():
    """
    Функция для парсинга заголовков новостей с Hacker News
    """

    # URL сайта для парсинга
    url = "https://news.ycombinator.com/"

    # Заголовки для имитации реального браузера (чтобы избежать блокировки)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        # Отправляем GET-запрос к сайту с таймаутом 10 секунд
        print(f"Отправка запроса к {url}...")
        response = requests.get(url, headers=headers, timeout=10)

        # Проверяем успешность запроса (код 200 означает успех)
        response.raise_for_status()

        print(f"Запрос выполнен успешно. Статус код: {response.status_code}")

        # Создаем объект BeautifulSoup для парсинга HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Находим все элементы с классом "titleline"
        # Именно в них содержатся заголовки новостей на Hacker News
        title_elements = soup.find_all('span', class_='titleline')

        # Проверяем, найдены ли элементы
        if not title_elements:
            print("Не удалось найти заголовки новостей. Возможно, структура сайта изменилась.")
            return

        print(f"Найдено заголовков: {len(title_elements)}")

        # Список для хранения заголовков
        titles = []

        # Извлекаем текст каждой ссылки внутри элементов titleline
        for i, element in enumerate(title_elements, 1):
            # Внутри span.titleline обычно находится тег <a> с заголовком
            link = element.find('a')
            if link:
                title_text = link.get_text(strip=True)  # Извлекаем текст и удаляем лишние пробелы
                titles.append(title_text)
                print(f"  {i}. {title_text[:50]}..." if len(title_text) > 50 else f"  {i}. {title_text}")

        # Сохраняем заголовки в текстовый файл
        output_filename = f"hacker_news_titles_{time.strftime('%Y%m%d_%H%M%S')}.txt"

        with open(output_filename, 'w', encoding='utf-8') as file:
            file.write(f"Заголовки новостей с Hacker News ({time.strftime('%Y-%m-%d %H:%M:%S')})\n")
            file.write("=" * 60 + "\n\n")

            for i, title in enumerate(titles, 1):
                file.write(f"{i}. {title}\n")

        print(f"\n✅ Заголовки успешно сохранены в файл: {output_filename}")
        print(f"Всего сохранено заголовков: {len(titles)}")

    except requests.exceptions.Timeout:
        print("❌ Ошибка: Превышен таймаут подключения. Сервер не отвечает.")
    except requests.exceptions.ConnectionError:
        print("❌ Ошибка: Не удалось подключиться к сайту. Проверьте интернет-соединение.")
    except requests.exceptions.HTTPError as http_err:
        print(f"❌ Ошибка HTTP: {http_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"❌ Ошибка при выполнении запроса: {req_err}")
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")


# Точка входа в программу
if __name__ == "__main__":
    print("=" * 60)
    print("Парсер заголовков новостей с Hacker News")
    print("=" * 60)

    # Вызываем основную функцию
    parse_hacker_news()

    print("\nПрограмма завершена.")