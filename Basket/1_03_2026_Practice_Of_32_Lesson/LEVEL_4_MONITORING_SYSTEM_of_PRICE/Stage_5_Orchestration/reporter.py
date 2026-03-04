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

from datetime import datetime, timedelta
import logging


class Reporter:
    """Класс для генерации отчетов"""

    def __init__(self, database):
        self.db = database
        self.logger = logging.getLogger(__name__)

    def generate_daily_report(self):
        """Генерация дневного отчета"""
        try:
            stats = self.db.get_today_stats()

            if not stats:
                return "  📭 Нет данных за сегодня"

            products_checked = stats[0] or 0
            total_checks = stats[1] or 0
            mock_checks = stats[2] or 0
            price_changes = stats[3] or 0
            avg_change = stats[4] or 0

            # Получаем список всех товаров
            products = self.db.get_all_products()

            report_lines = []
            report_lines.append(f"  📊 Статистика:")
            report_lines.append(f"     • Проверено товаров: {products_checked}")
            report_lines.append(f"     • Всего проверок: {total_checks}")
            report_lines.append(f"     • Тестовых данных: {mock_checks}")
            report_lines.append(f"     • Изменений цен: {price_changes}")

            if avg_change > 0:
                report_lines.append(f"     • Среднее изменение: {avg_change:.2f}%")

            if products:
                report_lines.append(f"\n  📦 Товары:")
                for i, product in enumerate(products[:5], 1):  # Показываем первые 5
                    name = product[1] or "Без названия"
                    price = product[2] or 0
                    currency = product[3] or "RUB"
                    last_check = product[4]

                    if last_check:
                        try:
                            dt = datetime.strptime(last_check, '%Y-%m-%d %H:%M:%S')
                            time_str = dt.strftime('%H:%M')
                        except:
                            time_str = "неизвестно"
                    else:
                        time_str = "неизвестно"

                    # Обрезаем длинные названия
                    short_name = name[:40] + "..." if len(name) > 40 else name
                    report_lines.append(f"     {i}. {short_name:40} {price:8.2f} {currency} [{time_str}]")

            return "\n".join(report_lines)

        except Exception as e:
            self.logger.error(f"❌ Ошибка генерации отчета: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return f"  ❌ Ошибка генерации отчета: {str(e)}"

    def generate_product_report(self, url):
        """Генерация отчета по конкретному товару"""
        try:
            data = self.db.get_product_with_changes(url)

            if not data['product']:
                return f"📭 Нет данных для {url}"

            product = data['product']
            changes = data['changes']

            # Распаковываем данные товара
            product_url, name, current_price, currency, last_timestamp, is_mock = product

            # Получаем историю цен для статистики
            history = self.db.get_price_history(url, limit=30)

            report_lines = []
            report_lines.append(f"\n  📈 Отчет по товару:")
            report_lines.append(f"  {'=' * 50}")
            report_lines.append(f"  📦 Название: {name}")
            report_lines.append(f"  🔗 URL: {url[:50]}..." if len(url) > 50 else f"  🔗 URL: {url}")

            if last_timestamp:
                report_lines.append(f"  ⏰ Последняя проверка: {last_timestamp}")

            if is_mock:
                report_lines.append(f"  ⚠️ Внимание: используются тестовые данные")

            # Статистика по ценам
            if history:
                prices = [h[0] for h in history]
                min_price = min(prices)
                max_price = max(prices)
                avg_price = sum(prices) / len(prices)

                report_lines.append(f"\n  📊 Статистика цен:")
                report_lines.append(f"     • Текущая: {current_price:.2f} {currency}")
                report_lines.append(f"     • Минимальная: {min_price:.2f} {currency}")
                report_lines.append(f"     • Максимальная: {max_price:.2f} {currency}")
                report_lines.append(f"     • Средняя: {avg_price:.2f} {currency}")

                if len(prices) > 1:
                    first_price = prices[-1]
                    change = ((current_price - first_price) / first_price) * 100
                    report_lines.append(f"     • Изменение за период: {change:+.2f}%")

            # Последние изменения
            if changes:
                report_lines.append(f"\n  🔄 Последние изменения:")
                for i, change in enumerate(changes[:5], 1):
                    old_price, new_price, change_percent, timestamp = change
                    arrow = "📈" if change_percent > 0 else "📉"
                    report_lines.append(
                        f"     {i}. {arrow} {old_price:.2f} → {new_price:.2f} {currency} ({change_percent:+.2f}%) [{timestamp}]")

            return "\n".join(report_lines)

        except Exception as e:
            self.logger.error(f"❌ Ошибка генерации отчета по товару: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return f"  ❌ Ошибка: {str(e)}"