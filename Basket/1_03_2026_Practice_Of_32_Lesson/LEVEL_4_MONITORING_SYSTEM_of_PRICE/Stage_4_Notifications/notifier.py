#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Промпт 4:
```
Напиши модуль notifier.py для отправки email-уведомлений.

Функция send_alert(product_name, url, current_price, threshold):
- Принимает данные о товаре и цене
- Формирует красивое HTML-письмо
- Отправляет через SMTP (настройки из конфига)
- Логирует успех/неудачу отправки

Функция send_daily_report(products_data):
- Принимает список всех товаров с текущими ценами
- Формирует сводку по всем товарам
- Отправляет одно письмо со статистикой

Используй библиотеку smtplib и email.mime.
Для тестирования можно использовать тестовый SMTP-сервер (например, Mailtrap).
```
'''

"""
Модуль для отправки email-уведомлений и ежедневных отчётов
по результатам мониторинга цен.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
from datetime import datetime
import os

# Настройка логирования
logger = logging.getLogger(__name__)


class EmailNotifier:
    """
    Класс для отправки email-уведомлений о изменении цен.
    Поддерживает отправку как отдельных уведомлений, так и ежедневных отчётов.
    """

    def __init__(self, email_config: Dict[str, str]):
        """
        Инициализация отправителя писем.

        Args:
            email_config: Словарь с настройками email
                {
                    'smtp_server': 'smtp.gmail.com',
                    'port': 587,
                    'sender': 'your-email@gmail.com',
                    'password': 'app-password',
                    'recipient': 'alert@example.com'
                }
        """
        self.config = email_config
        self.smtp_server = email_config['smtp_server']
        self.port = int(email_config['port'])
        self.sender = email_config['sender']
        self.password = email_config['password']
        self.recipient = email_config['recipient']

        # Проверяем обязательные поля
        self._validate_config()

    def _validate_config(self) -> None:
        """Проверяет наличие всех обязательных полей конфигурации"""
        required_fields = ['smtp_server', 'port', 'sender', 'password', 'recipient']
        missing = [field for field in required_fields if field not in self.config]

        if missing:
            raise ValueError(f"Отсутствуют обязательные поля конфигурации: {missing}")

    def _create_connection(self):
        """
        Создаёт соединение с SMTP-сервером.

        Returns:
            SMTP объект соединения
        """
        try:
            if self.port == 465:
                # SSL соединение
                server = smtplib.SMTP_SSL(self.smtp_server, self.port)
            else:
                # TLS соединение
                server = smtplib.SMTP(self.smtp_server, self.port)
                server.starttls()

            server.login(self.sender, self.password)
            logger.info(f"Успешное подключение к {self.smtp_server}")
            return server

        except smtplib.SMTPAuthenticationError:
            logger.error("Ошибка аутентификации. Проверьте логин и пароль.")
            raise
        except smtplib.SMTPException as e:
            logger.error(f"Ошибка SMTP: {e}")
            raise
        except Exception as e:
            logger.error(f"Ошибка подключения к серверу: {e}")
            raise

    def send_price_alert(self, product_name: str, url: str,
                         current_price: float, threshold: float) -> bool:
        """
        Отправляет уведомление о достижении пороговой цены.

        Args:
            product_name: Название товара
            url: Ссылка на товар
            current_price: Текущая цена
            threshold: Пороговое значение

        Returns:
            bool: True если отправка успешна, иначе False
        """
        subject = f"⚠️ ALERT: Цена достигла порога - {product_name}"

        body = f"""
        <h2>⚠️ Достигнут порог цены</h2>

        <p><strong>Товар:</strong> {product_name}</p>
        <p><strong>URL:</strong> <a href="{url}">{url}</a></p>
        <p><strong>Текущая цена:</strong> {current_price:.2f}</p>
        <p><strong>Пороговое значение:</strong> {threshold:.2f}</p>
        <p><strong>Время проверки:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <hr>
        <p><em>Система мониторинга цен</em></p>
        """

        return self._send_email(subject, body)

    def send_daily_report(self, products_data: List[Dict[str, Any]]) -> bool:
        """
        Отправляет ежедневный отчёт по всем отслеживаемым товарам.

        Args:
            products_data: Список словарей с данными о товарах
                Каждый словарь должен содержать:
                - 'name': название товара
                - 'url': ссылка на товар
                - 'current_price': текущая цена
                - 'previous_price': предыдущая цена (опционально)
                - 'threshold': пороговое значение
                - 'last_check': время последней проверки

        Returns:
            bool: True если отправка успешна, иначе False
        """
        if not products_data:
            logger.warning("Нет данных для формирования отчёта")
            return False

        # Формируем статистику
        stats = self._calculate_statistics(products_data)

        # Создаём тему письма с датой
        today = datetime.now().strftime('%Y-%m-%d')
        subject = f"📊 Ежедневный отчёт по мониторингу цен - {today}"

        # Формируем тело письма
        body = self._build_report_html(products_data, stats)

        return self._send_email(subject, body)

    def _calculate_statistics(self, products_data: List[Dict]) -> Dict[str, Any]:
        """
        Вычисляет статистику по товарам для отчёта.

        Args:
            products_data: Список данных о товарах

        Returns:
            Dict: Статистика (средняя цена, мин/макс, количество и т.д.)
        """
        stats = {
            'total_products': len(products_data),
            'products_with_price': 0,
            'products_below_threshold': 0,
            'products_price_dropped': 0,
            'products_price_increased': 0,
            'average_price': 0,
            'min_price': float('inf'),
            'min_price_product': None,
            'max_price': float('-inf'),
            'max_price_product': None,
            'total_price_change': 0
        }

        total_price = 0
        price_change_sum = 0

        for product in products_data:
            current = product.get('current_price')
            previous = product.get('previous_price')
            threshold = product.get('threshold')

            if current is not None:
                stats['products_with_price'] += 1
                total_price += current

                # Поиск минимальной цены
                if current < stats['min_price']:
                    stats['min_price'] = current
                    stats['min_price_product'] = product.get('name')

                # Поиск максимальной цены
                if current > stats['max_price']:
                    stats['max_price'] = current
                    stats['max_price_product'] = product.get('name')

                # Проверка порога
                if threshold and current <= threshold:
                    stats['products_below_threshold'] += 1

                # Анализ изменения цены
                if previous is not None:
                    change = current - previous
                    price_change_sum += abs(change)

                    if change < 0:
                        stats['products_price_dropped'] += 1
                    elif change > 0:
                        stats['products_price_increased'] += 1

            # Для товаров без цены
            if current is None and product.get('error'):
                stats.setdefault('products_with_error', 0)
                stats['products_with_error'] += 1

        # Вычисляем среднюю цену
        if stats['products_with_price'] > 0:
            stats['average_price'] = total_price / stats['products_with_price']

        # Сбрасываем min/max если они не были установлены
        if stats['min_price'] == float('inf'):
            stats['min_price'] = 0
        if stats['max_price'] == float('-inf'):
            stats['max_price'] = 0

        stats['total_price_change'] = round(price_change_sum, 2)

        return stats

    def _build_report_html(self, products_data: List[Dict],
                           stats: Dict[str, Any]) -> str:
        """
        Формирует HTML-содержимое для отчёта.

        Args:
            products_data: Список данных о товарах
            stats: Статистика по товарам

        Returns:
            str: HTML-код письма
        """
        today = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Начало HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
                h2 {{ color: #4CAF50; margin-top: 30px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th {{ background-color: #4CAF50; color: white; padding: 12px; text-align: left; }}
                td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
                tr:hover {{ background-color: #f5f5f5; }}
                .stats-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin: 20px 0;
                }}
                .stat-card {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 10px;
                    text-align: center;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }}
                .stat-card h3 {{ margin: 0; font-size: 14px; opacity: 0.9; }}
                .stat-card p {{ margin: 10px 0 0; font-size: 24px; font-weight: bold; }}
                .price-down {{ color: #f44336; }}
                .price-up {{ color: #4CAF50; }}
                .warning {{ background-color: #ff9800; color: white; padding: 10px; border-radius: 5px; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #777; }}
            </style>
        </head>
        <body>
            <h1>📊 Ежедневный отчёт по мониторингу цен</h1>
            <p><strong>Дата и время:</strong> {today}</p>
        """

        # Блок со статистикой
        html += """
            <h2>📈 Общая статистика</h2>
            <div class="stats-grid">
        """

        stat_cards = [
            ('Всего товаров', stats['total_products']),
            ('Цены получены', f"{stats['products_with_price']} / {stats['total_products']}"),
            ('Ниже порога', stats['products_below_threshold']),
            ('Средняя цена', f"{stats['average_price']:.2f} ₽" if stats['average_price'] else 'N/A'),
            ('Минимальная цена', f"{stats['min_price']:.2f} ₽<br><small>{stats['min_price_product'] or ''}</small>"),
            ('Максимальная цена', f"{stats['max_price']:.2f} ₽<br><small>{stats['max_price_product'] or ''}</small>"),
            ('Цена снизилась', stats['products_price_dropped']),
            ('Цена выросла', stats['products_price_increased']),
            ('Общее изменение', f"{stats['total_price_change']:.2f} ₽")
        ]

        for title, value in stat_cards:
            html += f"""
                <div class="stat-card">
                    <h3>{title}</h3>
                    <p>{value}</p>
                </div>
            """

        html += "</div>"

        # Таблица с товарами
        html += """
            <h2>📋 Детальная информация по товарам</h2>
            <table>
                <thead>
                    <tr>
                        <th>Товар</th>
                        <th>Текущая цена</th>
                        <th>Предыдущая цена</th>
                        <th>Изменение</th>
                        <th>Порог</th>
                        <th>Статус</th>
                    </tr>
                </thead>
                <tbody>
        """

        for product in products_data:
            name = product.get('name', 'Н/Д')
            url = product.get('url', '#')
            current = product.get('current_price')
            previous = product.get('previous_price')
            threshold = product.get('threshold')
            error = product.get('error')

            # Форматируем цены
            current_str = f"{current:.2f} ₽" if current is not None else "⚠️ Ошибка"
            previous_str = f"{previous:.2f} ₽" if previous is not None else "—"

            # Вычисляем изменение
            if current is not None and previous is not None:
                change = current - previous
                change_percent = (change / previous * 100) if previous != 0 else 0
                change_class = "price-down" if change < 0 else "price-up"
                change_str = f"<span class='{change_class}'>"
                change_str += f"{change:+.2f} ₽ ({change_percent:+.1f}%)"
                change_str += "</span>"
            else:
                change_str = "—"

            # Статус
            if current is not None and threshold is not None:
                if current <= threshold:
                    status = "⚠️ НИЖЕ ПОРОГА"
                else:
                    status = "✓ В норме"
            elif error:
                status = "❌ Ошибка"
            else:
                status = "—"

            html += f"""
                <tr>
                    <td><a href="{url}" target="_blank">{name}</a></td>
                    <td><strong>{current_str}</strong></td>
                    <td>{previous_str}</td>
                    <td>{change_str}</td>
                    <td>{f"{threshold} ₽" if threshold else "—"}</td>
                    <td>{status}</td>
                </tr>
            """

        html += """
                </tbody>
            </table>
        """

        # Добавляем информацию об ошибках, если есть
        if stats.get('products_with_error', 0) > 0:
            html += f"""
                <div class="warning">
                    ⚠️ Внимание: Для {stats['products_with_error']} товаров не удалось получить цену.
                </div>
            """

        # Подвал
        html += f"""
            <div class="footer">
                <p>Система мониторинга цен | Автоматический отчёт сгенерирован {today}</p>
                <p>Для настройки порогов измените файл конфигурации.</p>
            </div>
        </body>
        </html>
        """

        return html

    def _send_email(self, subject: str, html_body: str) -> bool:
        """
        Отправляет email с заданной темой и HTML-содержимым.

        Args:
            subject: Тема письма
            html_body: HTML-содержимое письма

        Returns:
            bool: True если отправка успешна, иначе False
        """
        try:
            # Создаём сообщение
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.sender
            msg['To'] = self.recipient

            # Добавляем HTML-версию
            part = MIMEText(html_body, 'html')
            msg.attach(part)

            # Отправляем
            with self._create_connection() as server:
                server.send_message(msg)

            logger.info(f"✅ Письмо успешно отправлено: {subject}")
            logger.info(f"   Получатель: {self.recipient}")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка отправки письма: {e}")
            return False


# Упрощённая функция для использования в main.py
def send_daily_report(products_data: List[Dict[str, Any]],
                      email_config: Dict[str, str]) -> bool:
    """
    Отправляет ежедневный отчёт по всем товарам.

    Args:
        products_data: Список товаров с ценами
        email_config: Настройки email из конфигурации

    Returns:
        bool: True если отправка успешна
    """
    notifier = EmailNotifier(email_config)
    return notifier.send_daily_report(products_data)


# Пример использования
if __name__ == "__main__":
    # Настройка логирования для примера
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Пример данных о товарах
    test_products = [
        {
            'name': 'Samsung Galaxy S6',
            'url': 'https://www.demoblaze.com/prod.html?idp_1',
            'current_price': 450.00,
            'previous_price': 500.00,
            'threshold': 400.00,
            'last_check': datetime.now().isoformat()
        },
        {
            'name': 'Nokia Lumia 1520',
            'url': 'https://www.demoblaze.com/prod.html?idp_2',
            'current_price': 320.00,
            'previous_price': 350.00,
            'threshold': 300.00,
            'last_check': datetime.now().isoformat()
        },
        {
            'name': 'Lenovo Yoga 720',
            'url': 'http://webscraper.io/test-sites/e-commerce/allinone/product/627',
            'current_price': 899.00,
            'previous_price': 899.00,
            'threshold': 850.00,
            'last_check': datetime.now().isoformat()
        },
        {
            'name': 'Товар с ошибкой',
            'url': 'https://example.com/error',
            'current_price': None,
            'error': 'Сайт недоступен',
            'threshold': 1000.00,
            'last_check': datetime.now().isoformat()
        }
    ]

    # Тестовая конфигурация email
    test_email_config = {
        'smtp_server': 'smtp.gmail.com',
        'port': 587,
        'sender': 'aleksejbaskirov31@gmail.com',
        'password': '',
        'recipient': 'aleksejbaskirom31@gmail.com.com'
    }

    print("🚀 Тестирование отправки ежедневного отчёта")
    print("=" * 60)

    # Отправляем отчёт
    success = send_daily_report(test_products, test_email_config)

    if success:
        print("\n✅ Тестовый отчёт успешно отправлен!")
    else:
        print("\n❌ Ошибка при отправке тестового отчёта")