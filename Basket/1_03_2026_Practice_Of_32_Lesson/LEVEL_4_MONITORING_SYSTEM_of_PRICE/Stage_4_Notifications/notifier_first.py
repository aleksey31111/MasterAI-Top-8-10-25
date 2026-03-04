import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict, Any

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация почты
email_config = {
    'smtp_server': 'smtp.gmail.com',
    'port': 587,
    'sender': 'aleksejbaskirov31@gmail.com',
    'password': 'passwordtoemailok',  # Пароль приложения
    'recipient': 'aleksejbaskirov31@gmail.com'  # Отправляем себе же для теста
}


class EmailNotifier:
    """Класс для отправки email-уведомлений"""

    def __init__(self, config: dict):
        self.config = config
        self.smtp_server = config['smtp_server']
        self.port = config['port']
        self.sender = config['sender']
        self.password = config['password'].replace(' ', '')  # Убираем пробелы из пароля
        self.recipient = config['recipient']

        logger.info(f"Инициализирован EmailNotifier для {self.sender} -> {self.recipient}")

    def send_email(self, subject: str, html_content: str) -> bool:
        """
        Отправка email с HTML-содержимым

        Args:
            subject: Тема письма
            html_content: HTML-содержимое письма

        Returns:
            bool: True если отправка успешна, False в противном случае
        """
        try:
            # Создаем сообщение
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.sender
            msg['To'] = self.recipient

            # Прикрепляем HTML-версию
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)

            # Подключаемся к серверу и отправляем
            logger.info(f"Подключение к SMTP серверу {self.smtp_server}:{self.port}")

            with smtplib.SMTP(self.smtp_server, self.port) as server:
                server.starttls()  # Включаем TLS
                server.login(self.sender, self.password)
                server.send_message(msg)

            logger.info(f"Письмо успешно отправлено: {subject}")
            return True

        except Exception as e:
            logger.error(f"Ошибка при отправке письма: {e}")
            return False

    def send_price_alert(self, product_name: str, old_price: float, new_price: float, url: str) -> bool:
        """
        Отправка уведомления о снижении цены
        """
        subject = f"🔔 СНИЖЕНИЕ ЦЕНЫ: {product_name}"

        # Исправленный HTML-шаблон (без проблем с форматированием)
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .container {{
                    background-color: #f9f9f9;
                    border-radius: 10px;
                    padding: 20px;
                    border: 1px solid #ddd;
                }}
                .header {{
                    background-color: #4CAF50;
                    color: white;
                    padding: 10px;
                    text-align: center;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }}
                .product-name {{
                    font-size: 18px;
                    font-weight: bold;
                    margin-bottom: 15px;
                }}
                .price-old {{
                    color: #999;
                    text-decoration: line-through;
                    font-size: 16px;
                }}
                .price-new {{
                    color: #4CAF50;
                    font-size: 24px;
                    font-weight: bold;
                }}
                .discount {{
                    background-color: #ff6b6b;
                    color: white;
                    padding: 5px 10px;
                    border-radius: 5px;
                    display: inline-block;
                    margin: 10px 0;
                }}
                .button {{
                    display: inline-block;
                    padding: 10px 20px;
                    background-color: #4CAF50;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin-top: 15px;
                }}
                .footer {{
                    margin-top: 20px;
                    font-size: 12px;
                    color: #999;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>⚠️ СНИЖЕНИЕ ЦЕНЫ ⚠️</h2>
                </div>

                <div class="product-name">{product_name}</div>

                <div class="price-old">Старая цена: {old_price:.2f} руб.</div>
                <div class="price-new">Новая цена: {new_price:.2f} руб.</div>

                <div class="discount">
                    Скидка: {((old_price - new_price) / old_price * 100):.1f}%
                </div>

                <p>Вы экономите: <strong>{old_price - new_price:.2f} руб.</strong></p>

                <a href="{url}" class="button">Перейти к товару</a>

                <div class="footer">
                    <p>Это автоматическое уведомление с сайта мониторинга цен.</p>
                    <p>Отправлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
                </div>
            </div>
        </body>
        </html>
        """

        return self.send_email(subject, html_content)

    def send_daily_report(self, products: List[Dict[str, Any]]) -> bool:
        """
        Отправка ежедневного отчёта по всем товарам
        """
        subject = f"📊 Ежедневный отчёт по ценам - {datetime.now().strftime('%d.%m.%Y')}"

        # Генерируем HTML для списка товаров
        products_html = ""
        for i, product in enumerate(products, 1):
            products_html += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">{i}</td>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">{product.get('name', 'Нет названия')}</td>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">{product.get('price', 0):.2f} руб.</td>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">
                    <a href="{product.get('url', '#')}" style="color: #4CAF50;">Ссылка</a>
                </td>
            </tr>
            """

        # Вычисляем среднюю цену
        avg_price = 0
        if products:
            total = sum(p.get('price', 0) for p in products)
            avg_price = total / len(products)

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .container {{
                    background-color: #ffffff;
                    border-radius: 10px;
                    padding: 20px;
                    border: 1px solid #e0e0e0;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                    margin: -20px -20px 20px -20px;
                }}
                .stats {{
                    display: flex;
                    justify-content: space-around;
                    margin: 20px 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                    border-radius: 10px;
                }}
                .stat-item {{
                    text-align: center;
                }}
                .stat-value {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #667eea;
                }}
                .stat-label {{
                    font-size: 14px;
                    color: #666;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                th {{
                    background-color: #667eea;
                    color: white;
                    padding: 12px;
                    text-align: left;
                }}
                td {{
                    padding: 10px;
                    border-bottom: 1px solid #ddd;
                }}
                tr:hover {{
                    background-color: #f5f5f5;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    font-size: 12px;
                    color: #999;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Ежедневный отчёт по ценам</h1>
                    <p>Отчёт за {datetime.now().strftime('%d.%m.%Y')}</p>
                </div>

                <div class="stats">
                    <div class="stat-item">
                        <div class="stat-value">{len(products)}</div>
                        <div class="stat-label">Всего товаров</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{sum(p.get('price', 0) for p in products):.0f} руб.</div>
                        <div class="stat-label">Общая сумма</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{avg_price:.0f} руб.</div>
                        <div class="stat-label">Средняя цена</div>
                    </div>
                </div>

                <h3>📋 Список отслеживаемых товаров:</h3>

                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Название</th>
                            <th>Цена</th>
                            <th>Ссылка</th>
                        </tr>
                    </thead>
                    <tbody>
                        {products_html}
                    </tbody>
                </table>

                <div class="footer">
                    <p>Автоматическая рассылка от системы мониторинга цен</p>
                    <p>Для отключения уведомлений обратитесь к администратору</p>
                </div>
            </div>
        </body>
        </html>
        """

        return self.send_email(subject, html_content)

    def send_test_email(self) -> bool:
        """
        Отправка тестового письма для проверки работоспособности
        """
        subject = "🔧 Тестовое письмо от Notifier"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .container {{
                    background-color: #f0f8ff;
                    border-radius: 10px;
                    padding: 20px;
                    border: 2px solid #4CAF50;
                }}
                h1 {{
                    color: #4CAF50;
                    text-align: center;
                }}
                .success {{
                    background-color: #dff0d8;
                    color: #3c763d;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                    text-align: center;
                    font-size: 18px;
                }}
                .info {{
                    background-color: #d9edf7;
                    color: #31708f;
                    padding: 10px;
                    border-radius: 5px;
                    margin: 10px 0;
                }}
                .footer {{
                    margin-top: 20px;
                    font-size: 12px;
                    color: #999;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>✅ Тестовое письмо</h1>

                <div class="success">
                    <strong>Успех!</strong> Ваш EmailNotifier работает корректно.
                </div>

                <div class="info">
                    <p><strong>Информация о системе:</strong></p>
                    <ul>
                        <li>Время отправки: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</li>
                        <li>Отправитель: {self.sender}</li>
                        <li>Получатель: {self.recipient}</li>
                    </ul>
                </div>

                <p>Это тестовое письмо подтверждает, что:</p>
                <ul>
                    <li>✓ SMTP-соединение работает</li>
                    <li>✓ Аутентификация успешна</li>
                    <li>✓ HTML-шаблоны корректны</li>
                    <li>✓ Кодировка UTF-8 поддерживается</li>
                </ul>

                <div class="footer">
                    <p>Это автоматическое сообщение, пожалуйста, не отвечайте на него.</p>
                    <p>© 2026 Система мониторинга цен</p>
                </div>
            </div>
        </body>
        </html>
        """

        return self.send_email(subject, html_content)


def main():
    """Основная функция для тестирования"""
    print("=" * 60)
    print("🔧 ТЕСТИРОВАНИЕ NOTIFIER.PY")
    print("=" * 60)

    # Создаем экземпляр уведомителя
    notifier = EmailNotifier(email_config)

    # Тест 1: Отправка тестового письма
    print("\n📧 Тест 1: Отправка тестового письма")
    print("-" * 40)
    if notifier.send_test_email():
        print("✅ Тестовое письмо отправлено успешно")
    else:
        print("❌ Ошибка отправки тестового письма")

    # Тест 2: Уведомление о снижении цены
    print("\n🔔 Тест 2: Уведомление о снижении цены")
    print("-" * 40)
    if notifier.send_price_alert(
            product_name="Смартфон Xiaomi Mi 11",
            old_price=59990.00,
            new_price=49990.00,
            url="https://example.com/product/123"
    ):
        print("✅ Уведомление о снижении цены отправлено")
    else:
        print("❌ Ошибка отправки уведомления о снижении цены")

    # Тест 3: Ежедневный отчёт
    print("\n📊 Тест 3: Ежедневный отчёт")
    print("-" * 40)

    # Тестовые данные
    test_products = [
        {
            'name': 'Смартфон Xiaomi Mi 11',
            'price': 49990.00,
            'url': 'https://example.com/xiaomi-mi-11'
        },
        {
            'name': 'Ноутбук Lenovo ThinkPad',
            'price': 89990.00,
            'url': 'https://example.com/lenovo-thinkpad'
        },
        {
            'name': 'Наушники Sony WH-1000XM4',
            'price': 27990.00,
            'url': 'https://example.com/sony-wh1000xm4'
        }
    ]

    if notifier.send_daily_report(test_products):
        print("✅ Ежедневный отчёт отправлен")
    else:
        print("❌ Ошибка отправки ежедневного отчёта")

    print("\n" + "=" * 60)
    print("✅ Тестирование завершено")
    print("=" * 60)


if __name__ == "__main__":
    main()