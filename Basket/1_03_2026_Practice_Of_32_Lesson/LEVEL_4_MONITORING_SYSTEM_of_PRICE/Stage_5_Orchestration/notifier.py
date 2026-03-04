'''
Этап 5: Оркестрация

Промпт 5:
```
Напиши main.py, который объединяет все модули системы мониторинга цен.

Алгоритм работы:
1. Загрузить конфиг
2. Инициализировать БД
3. Для каждого URL из конфига:
   - Получить текущую цену
   - Если цена изменилась, сохранить в историю
   - Если цена упала ниже порога, отправить уведомление
4. После обработки всех URL, отправить дневной отчет
5. Записать в лог время выполнения и количество обработанных товаров

Добавь возможность однократного запуска (для cron) и режима бесконечного цикла с интервалом из конфига.

Используй аргументы командной строки:
python main.py --once (однократный запуск)
python main.py --daemon (бесконечный цикл)
```
'''

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import logging
from datetime import datetime
import os


class Notifier:
    """Класс для отправки уведомлений"""

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def send_alert(self, product_name, current_price, threshold, url):
        """Отправка уведомления о снижении цены"""

        # Создаем красивое сообщение
        message = self._format_alert_message(product_name, current_price, threshold, url)

        # Вывод в консоль (всегда)
        self._send_console("🚨 СНИЖЕНИЕ ЦЕНЫ", message)

        # Остальные каналы по настройкам
        self._send_notifications("🚨 ALERT: " + product_name, message)

    def send_daily_report(self, report):
        """Отправка дневного отчета"""

        date_str = datetime.now().strftime('%Y-%m-%d')
        message = self._format_report_message(report)

        # Вывод в консоль
        self._send_console(f"📊 ДНЕВНОЙ ОТЧЕТ {date_str}", message)

        # Остальные каналы
        self._send_notifications(f"📊 Daily Report {date_str}", message)

        # Сохраняем отчет в файл
        self._save_report_to_file(report, date_str)

    def _format_alert_message(self, product_name, current_price, threshold, url):
        """Форматирование сообщения об alert"""
        return f"""
╔══════════════════════════════════════════════════════════╗
║                     🚨 ALERT                             ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  📦 Товар: {product_name[:50]}...          ║
║  💰 Текущая цена: {current_price:.2f} руб.                ║
║  📉 Порог: {threshold:.2f} руб.                           ║
║  🔗 Ссылка: {url[:50]}...              ║
║  ⏰ Время: {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}     ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
        """

    def _format_report_message(self, report):
        """Форматирование отчета"""
        return f"""
╔══════════════════════════════════════════════════════════╗
║              📊 ДНЕВНОЙ ОТЧЕТ МОНИТОРИНГА                ║
║                    {datetime.now().strftime('%d.%m.%Y')}                      ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
{report}
║                                                          ║
╚══════════════════════════════════════════════════════════╝
        """

    def _send_console(self, title, message):
        """Вывод в консоль"""
        print(f"\n{title}")
        print(message)
        self.logger.info(f"📢 Уведомление выведено в консоль: {title}")

    def _send_notifications(self, subject, message):
        """Отправка уведомлений по всем настроенным каналам"""

        # Email уведомления
        if self.config.get('email', {}).get('enabled'):
            self._send_email(subject, message)

        # Telegram уведомления
        if self.config.get('telegram', {}).get('enabled'):
            self._send_telegram(message)

    def _send_email(self, subject, message):
        """Отправка email уведомления"""
        try:
            email_config = self.config['email']

            msg = MIMEMultipart()
            msg['From'] = email_config['sender']
            msg['To'] = ', '.join(email_config['recipients'])
            msg['Subject'] = subject

            msg.attach(MIMEText(message, 'plain', 'utf-8'))

            # Подключение к SMTP серверу
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['sender'], email_config['password'])

            # Отправка письма
            server.send_message(msg)
            server.quit()

            self.logger.info(f"✅ Email отправлен: {subject}")

        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки email: {e}")

    def _send_telegram(self, message):
        """Отправка Telegram уведомления"""
        try:
            telegram_config = self.config['telegram']

            url = f"https://api.telegram.org/bot{telegram_config['bot_token']}/sendMessage"
            data = {
                'chat_id': telegram_config['chat_id'],
                'text': message,
                'parse_mode': 'HTML'
            }

            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()

            self.logger.info("✅ Telegram отправлен")

        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки Telegram: {e}")

    def _save_report_to_file(self, report, date_str):
        """Сохранение отчета в файл"""
        try:
            report_dir = 'reports'
            if not os.path.exists(report_dir):
                os.makedirs(report_dir)

            filename = f"{report_dir}/report_{date_str}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)

            self.logger.info(f"💾 Отчет сохранен в {filename}")

        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения отчета: {e}")