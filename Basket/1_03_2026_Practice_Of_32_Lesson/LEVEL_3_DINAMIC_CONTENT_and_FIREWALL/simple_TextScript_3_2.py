# quick_test.py - быстрая проверка
import cloudscraper
import requests

# Список для проверки
test_urls = [
    "http://httpbin.org/status/200",  # Простой тест
    "https://nowsecure.nl/",
    "http://cf-test.sy1.me/",
]

scraper = cloudscraper.create_scraper()

for url in test_urls:
    print(f"\n📌 Тест: {url}")

    # Requests
    try:
        r = requests.get(url, timeout=5)
        print(f"  requests: {r.status_code}")
    except:
        print("  requests: ❌ Ошибка")

    # Cloudscraper
    try:
        c = scraper.get(url, timeout=10)
        print(f"  cloudscraper: {c.status_code} ({len(c.content)} байт)")
    except:
        print("  cloudscraper: ❌ Ошибка")