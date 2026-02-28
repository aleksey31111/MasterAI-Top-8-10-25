# Импортируем библиотеку requests для отправки HTTP-запросов
import requests

# 1. URL целевой страницы
# Это адрес сайта, с которым мы будем работать
url = "http://quotes.toscrape.com"

# 2. Отправляем GET-запрос на сервер
# Функция get() отправляет запрос и ожидает ответ от сервера
response = requests.get(url)

# 3. Проверяем успешность запроса
# Атрибут status_code содержит HTTP-код ответа. Код 200 означает "OK"
if response.status_code == 200:
    # Если запрос успешен, выводим подтверждение
    print(f"✅ Запрос успешен! Код статуса: {response.status_code}")

    # 4. Выводим заголовок страницы
    # Сначала получаем HTML-код страницы как текст
    html_content = response.text
    # Ищем открывающий тег <title> и закрывающий </title>
    start_tag = '<title>'
    end_tag = '</title>'

    # Находим позицию (индекс) начала тега <title>
    start_index = html_content.find(start_tag)
    # Находим позицию начала тега </title>
    end_index = html_content.find(end_tag)

    # Если оба тега найдены (индексы не равны -1)
    if start_index != -1 and end_index != -1:
        # Извлекаем текст между тегами
        # start_index + len(start_tag) - это позиция сразу после <title>
        title_text = html_content[start_index + len(start_tag):end_index]
        print(f"📰 Заголовок страницы: {title_text}")
    else:
        print("❌ Не удалось найти заголовок на странице")

    # 5. Сохраняем HTML-код в файл
    # Открываем файл 'page_content.html' для записи ('w') с кодировкой UTF-8
    with open('page_content.html', 'w', encoding='utf-8') as file:
        # Записываем весь HTML-код в файл
        file.write(html_content)

    # Подтверждаем сохранение файла
    print("💾 HTML-код успешно сохранён в файл 'page_content.html'")

# Если код статуса не 200 (например, 404 - страница не найдена, 500 - ошибка сервера)
else:
    print(f"❌ Ошибка при запросе. Код статуса: {response.status_code}")