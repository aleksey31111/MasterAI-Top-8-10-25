#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Промпт 1:
```
Создай структуру проекта для системы мониторинга цен. Нужны следующие модули:

1. config.py - загрузка конфигурации из JSON-файла
2. scraper.py - парсинг цен с сайта
3. database.py - работа с SQLite (сохранение и получение цен)
4. notifier.py - отправка email-уведомлений
5. main.py - основной скрипт, координирующий работу

Напиши только файл config.py, который:
- Загружает данные из config.json (пример файла предоставь)
- Проверяет наличие всех необходимых полей
- Возвращает объект с настройками

Пример config.json:
{
    "urls": [
        "https://example.com/product1",
        "https://example.com/product2"
    ],
    "thresholds": {
        "https://example.com/product1": 50000,
        "https://example.com/product2": 30000
    },
    "email": {
        "smtp_server": "smtp.gmail.com",
        "port": 587,
        "sender": "myemail@gmail.com",
        "password": "app_password",
        "recipient": "alert@example.com"
    },
    "check_interval": 24
}
```
'''
"""
Модуль конфигурации для системы мониторинга цен.
Адаптирован для тестирования на Demoblaze и других демо-сайтах.
"""

import json
from typing import Dict, List, Any, Optional
from pathlib import Path


class ConfigError(Exception):
    """Исключение для ошибок конфигурации"""
    pass


class Config:
    """
    Класс для загрузки и хранения конфигурации мониторинга цен.

    Теперь поддерживает:
    - Разные селекторы для разных сайтов
    - Специфические для Demoblaze настройки
    """

    # Обязательные поля в конфигурации
    REQUIRED_FIELDS = ['sites', 'email', 'check_interval']

    # Обязательные поля для каждого сайта
    REQUIRED_SITE_FIELDS = ['url', 'name', 'price_selector', 'currency']

    # Обязательные поля в секции email
    REQUIRED_EMAIL_FIELDS = ['smtp_server', 'port', 'sender', 'password', 'recipient']

    def __init__(self, config_path: str = 'config.json'):
        """
        Инициализация конфигурации.

        Args:
            config_path: Путь к файлу конфигурации

        Raises:
            ConfigError: Если конфигурация некорректна
        """
        self.config_path = config_path
        self.raw_config: Dict[str, Any] = {}

        # Загружаем конфигурацию
        self._load_config()

        # Проверяем наличие обязательных полей
        self._validate_config()

        # Инициализируем атрибуты
        self.sites: List[Dict] = self.raw_config['sites']
        self.email_config: Dict[str, str] = self.raw_config['email']
        self.check_interval: int = self.raw_config['check_interval']

        # Дополнительные проверки
        self._validate_sites()
        self._validate_email()
        self._validate_interval()

    def _load_config(self) -> None:
        """Загружает конфигурацию из JSON-файла"""
        config_path = Path(self.config_path)

        if not config_path.exists():
            raise ConfigError(f"Файл конфигурации не найден: {self.config_path}")

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.raw_config = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigError(f"Ошибка парсинга JSON: {e}")
        except Exception as e:
            raise ConfigError(f"Ошибка при чтении файла: {e}")

    def _validate_config(self) -> None:
        """Проверяет наличие всех обязательных полей"""
        missing_fields = []
        for field in self.REQUIRED_FIELDS:
            if field not in self.raw_config:
                missing_fields.append(field)

        if missing_fields:
            raise ConfigError(f"Отсутствуют поля: {', '.join(missing_fields)}")

    def _validate_sites(self) -> None:
        """
        Проверяет корректность настроек сайтов.
        Специальная обработка для Demoblaze.
        """
        sites = self.raw_config['sites']

        if not isinstance(sites, list):
            raise ConfigError("Поле 'sites' должно быть списком")

        if len(sites) == 0:
            raise ConfigError("Список сайтов не может быть пустым")

        for i, site in enumerate(sites):
            # Проверяем обязательные поля
            missing_fields = []
            for field in self.REQUIRED_SITE_FIELDS:
                if field not in site:
                    missing_fields.append(field)

            if missing_fields:
                raise ConfigError(
                    f"Сайт #{i + 1} не имеет полей: {', '.join(missing_fields)}"
                )

            # Проверяем URL
            if not site['url'].startswith(('http://', 'https://')):
                raise ConfigError(f"Некорректный URL для сайта #{i + 1}: {site['url']}")

            # Проверяем порог (если есть)
            if 'threshold' in site:
                if not isinstance(site['threshold'], (int, float)):
                    raise ConfigError(f"Порог для сайта #{i + 1} должен быть числом")
                if site['threshold'] <= 0:
                    raise ConfigError(f"Порог для сайта #{i + 1} должен быть положительным")

            # Специальная проверка для Demoblaze
            if 'demoblaze' in site['url'].lower() or site['name'].lower() == 'demoblaze':
                self._validate_demoblaze_site(site, i + 1)

    def _validate_demoblaze_site(self, site: Dict, site_num: int) -> None:
        """
        Специфические проверки для Demoblaze.

        Args:
            site: Настройки сайта
            site_num: Номер сайта для сообщений об ошибках
        """
        # Проверяем формат цены для Demoblaze
        if 'price_format' in site:
            if site['price_format'] not in ['$', 'USD', 'dollar']:
                raise ConfigError(
                    f"Для Demoblaze (сайт #{site_num}) цена должна быть в долларах ($)"
                )

        # Рекомендуемый селектор для Demoblaze
        if site['price_selector'] != '.price-container':
            print(f"⚠️ Внимание: Для Demoblaze (сайт #{site_num}) рекомендуется селектор '.price-container'")

    def _validate_email(self) -> None:
        """Проверяет корректность настроек email"""
        email_config = self.raw_config['email']

        if not isinstance(email_config, dict):
            raise ConfigError("Поле 'email' должно быть объектом")

        missing_fields = []
        for field in self.REQUIRED_EMAIL_FIELDS:
            if field not in email_config:
                missing_fields.append(field)

        if missing_fields:
            raise ConfigError(f"В email отсутствуют: {', '.join(missing_fields)}")

        # Проверяем порт
        try:
            port = int(email_config['port'])
            if port <= 0 or port > 65535:
                raise ConfigError(f"Некорректный порт: {port}")
        except ValueError:
            raise ConfigError(f"Порт должен быть числом")

        # Проверяем, что поля не пустые
        for field in ['smtp_server', 'sender', 'password', 'recipient']:
            if not email_config[field]:
                raise ConfigError(f"Поле email.{field} не может быть пустым")

    def _validate_interval(self) -> None:
        """Проверяет интервал проверки"""
        interval = self.raw_config['check_interval']

        if not isinstance(interval, (int, float)):
            raise ConfigError(f"check_interval должен быть числом")

        if interval <= 0:
            raise ConfigError(f"check_interval должен быть положительным")

        if interval > 168:  # Максимум неделя
            print(f"⚠️ Внимание: Интервал {interval}ч больше недели")

    def get_sites(self) -> List[Dict]:
        """Возвращает список сайтов для мониторинга"""
        return self.sites.copy()

    def get_demoblaze_sites(self) -> List[Dict]:
        """Возвращает только сайты Demoblaze (для специальной обработки)"""
        return [
            site for site in self.sites
            if 'demoblaze' in site['url'].lower() or site['name'].lower() == 'demoblaze'
        ]

    def get_price_selector(self, url: str) -> Optional[str]:
        """Возвращает селектор цены для конкретного URL"""
        for site in self.sites:
            if site['url'] == url:
                return site.get('price_selector')
        return None

    def get_threshold(self, url: str) -> Optional[float]:
        """Возвращает порог для конкретного URL"""
        for site in self.sites:
            if site['url'] == url:
                return site.get('threshold')
        return None

    def get_email_config(self) -> Dict[str, str]:
        """Возвращает копию настроек email"""
        return self.email_config.copy()

    def get_check_interval(self) -> int:
        """Возвращает интервал проверки в часах"""
        return self.check_interval

    def __repr__(self) -> str:
        """Строковое представление"""
        email_masked = self.email_config.copy()
        email_masked['password'] = '********'

        return (
            f"Config(\n"
            f"  sites={len(self.sites)} сайтов,\n"
            f"  email={email_masked},\n"
            f"  check_interval={self.check_interval}\n"
            f")"
        )


def create_example_config(filename: str = 'config.example.json') -> None:
    """
    Создаёт пример файла конфигурации с Demoblaze и другими тестовыми сайтами.
    """
    example_config = {
        "sites": [
            {
                "name": "Demoblaze - Samsung Galaxy s6",
                "url": "https://www.demoblaze.com/prod.html?idp_1",
                "price_selector": ".price-container",
                "currency": "$",
                "threshold": 500,
                "description": "Телефон Samsung для тестирования"
            },
            {
                "name": "Demoblaze - Nokia lumia 1520",
                "url": "https://www.demoblaze.com/prod.html?idp_2",
                "price_selector": ".price-container",
                "currency": "$",
                "threshold": 300,
                "description": "Телефон Nokia для тестирования"
            },
            {
                "name": "Demoblaze - Nexus 6",
                "url": "https://www.demoblaze.com/prod.html?idp_3",
                "price_selector": ".price-container",
                "currency": "$",
                "threshold": 400,
                "description": "Телефон Nexus для тестирования"
            },
            {
                "name": "Books to Scrape - A Light in the Attic",
                "url": "http://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
                "price_selector": ".price_color",
                "currency": "£",
                "threshold": 50,
                "description": "Книга для тестирования"
            },
            {
                "name": "WebScraper - Laptop",
                "url": "https://webscraper.io/test-sites/e-commerce/allinone/product/626",
                "price_selector": ".price",
                "currency": "$",
                "threshold": 400,
                "description": "Ноутбук для тестирования"
            }
        ],
        "email": {
            "smtp_server": "smtp.gmail.com",
            "port": 587,
            "sender": "your-test-email@gmail.com",
            "password": "your-app-password",
            "recipient": "your-alert-email@example.com"
        },
        "check_interval": 24,
        "settings": {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "request_delay": 2,
            "retry_attempts": 3
        }
    }

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(example_config, f, indent=4, ensure_ascii=False)

    print(f"✅ Пример конфигурации создан в файле: {filename}")
    print("📌 Включает тестовые сайты: Demoblaze, Books to Scrape, WebScraper")
    print("⚠️ Не забудьте заменить email-настройки на реальные!")


# Пример использования
if __name__ == "__main__":
    # Создаём пример конфигурации
    create_example_config()

    # Пробуем загрузить
    try:
        config = Config('config.example.json')
        print("\n✅ Конфигурация успешно загружена:")
        print(config)

        # Показываем сайты
        print("\n📊 Отслеживаемые сайты:")
        for site in config.get_sites():
            print(f"  • {site['name']}: {site['url']}")
            print(f"    Селектор: '{site['price_selector']}', Порог: {site.get('threshold', 'не задан')}")

        # Показываем сайты Demoblaze
        demoblaze_sites = config.get_demoblaze_sites()
        if demoblaze_sites:
            print(f"\n📱 Найдено сайтов Demoblaze: {len(demoblaze_sites)}")
            for site in demoblaze_sites:
                print(f"    - {site['name']}")

    except ConfigError as e:
        print(f"\n❌ Ошибка конфигурации: {e}")
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")