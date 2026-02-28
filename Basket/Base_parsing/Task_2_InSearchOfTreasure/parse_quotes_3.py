# Импортируем библиотеки: requests для запросов, BeautifulSoup для парсинга HTML
import requests
from bs4 import BeautifulSoup

# URL целевой страницы
url = "http://quotes.toscrape.com"

# Отправляем GET-запрос
response = requests.get(url)

# Проверяем успешность запроса
if response.status_code == 200:
    print(f"✅ Запрос успешен! Начинаем парсинг...\n")

    # Создаём "суп" — объект BeautifulSoup для парсинга HTML
    # Первый аргумент — HTML-код страницы (response.text)
    # Второй аргумент — парсер ('html.parser' встроенный, можно 'lxml' для скорости)
    soup = BeautifulSoup(response.text, 'html.parser')

    # *** МАГИЯ find_all() ***
    # Метод find_all() ищет ВСЕ элементы HTML, соответствующие заданным критериям.
    # Здесь мы ищем все теги <div> с атрибутом class="quote".
    # Результат — список (list) найденных элементов (объектов Tag).
    quotes_list = soup.find_all('div', class_='quote')

    # Выводим информацию о количестве найденных цитат
    print(f"Найдено цитат на странице: {len(quotes_list)}\n")
    print("-" * 60)

    # Перебираем все найденные элементы-цитаты в цикле
    for i, quote in enumerate(quotes_list, 1):
        # *** ИЗВЛЕКАЕМ ТЕКСТ ЦИТАТЫ ***
        # 1. Сначала внутри текущего <div class="quote"> ищем первый (и единственный) тег <span class="text">.
        #    Для этого используем метод find(), который ищет ТОЛЬКО ПЕРВЫЙ подходящий элемент.
        # 2. У найденного элемента берём его текст через .text
        # 3. Убираем лишние пробелы и переносы строк по краям с помощью .strip()
        text_element = quote.find('span', class_='text')
        quote_text = text_element.text.strip() if text_element else "Текст не найден"

        # *** ИЗВЛЕКАЕМ АВТОРА ***
        # Аналогично: ищем первый тег <small class="author"> внутри текущей цитаты
        author_element = quote.find('small', class_='author')
        author = author_element.text.strip() if author_element else "Автор не найден"

        # *** ИЗВЛЕКАЕМ ТЕГИ ***
        # Здесь снова пригождается find_all().
        # Внутри цитаты все теги находятся в элементах <a class="tag">.
        # Мы находим ВСЕ такие элементы и собираем их текст в список.
        tag_elements = quote.find_all('a', class_='tag')
        tags = [tag.text for tag in tag_elements]  # Генератор списка: для каждого тега берём его текст

        # Форматируем теги для вывода
        tags_str = ', '.join(tags) if tags else 'Тегов нет'

        # Выводим результат
        print(f"Цитата {i}: \"{quote_text}\"")
        print(f"   Автор: {author}")
        print(f"   Теги: {tags_str}")
        print("-" * 60)

else:
    print(f"❌ Ошибка при запросе. Код статуса: {response.status_code}")
