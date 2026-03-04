#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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

import argparse
import time
import logging
from datetime import datetime
import sys
import os
import signal

# Импорты модулей системы
from config import Config
from database import Database
from parser import PriceParser
from notifier import Notifier
from logger import setup_logger
from reporter import Reporter


class PriceMonitor:
    """Основной класс оркестрации системы мониторинга цен"""

    def __init__(self):
        """Инициализация компонентов системы"""

        # Создание необходимых директорий
        self._create_directories()

        # Настройка логирования
        self.logger = setup_logger('price_monitor')
        self.logger.info("=" * 60)
        self.logger.info("ЗАПУСК СИСТЕМЫ МОНИТОРИНГА ЦЕН (УЧЕБНАЯ ВЕРСИЯ)")
        self.logger.info("=" * 60)

        # Загрузка конфигурации
        try:
            self.config = Config()
            self.logger.info("✅ Конфигурация успешно загружена")
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки конфигурации: {e}")
            sys.exit(1)

        # Инициализация базы данных
        try:
            self.db = Database(self.config.db_path)
            self.db.initialize()
            self.logger.info(f"✅ База данных инициализирована: {self.config.db_path}")
        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации БД: {e}")
            sys.exit(1)

        # Инициализация парсера
        self.parser = PriceParser(self.config)

        # Инициализация уведомлений
        self.notifier = Notifier(self.config.notification_config)

        # Инициализация отчета
        self.reporter = Reporter(self.db)

        # Флаг для graceful shutdown
        self.running = True
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.logger.info("✅ Все компоненты системы инициализированы")
        self.logger.info("=" * 60)

    def _create_directories(self):
        """Создание необходимых директорий"""
        directories = ['logs', 'data']

        for directory in directories:
            if not os.path.exists(directory):
                try:
                    os.makedirs(directory)
                    print(f"📁 Создана директория: {directory}")
                except Exception as e:
                    print(f"❌ Ошибка создания директории {directory}: {e}")

    def _signal_handler(self, signum, frame):
        """Обработчик сигналов для graceful shutdown"""
        self.logger.info("🛑 Получен сигнал остановки. Завершение работы...")
        self.running = False

    def process_product(self, item):
        """
        Обработка одного товара

        Args:
            item (dict): Данные товара из конфига

        Returns:
            dict: Результат обработки или None в случае ошибки
        """
        url = item['url']
        name = item.get('name', 'Неизвестный товар')
        threshold = item.get('threshold')
        selectors = {
            'price_selector': item.get('price_selector'),
            'name_selector': item.get('name_selector')
        }

        try:
            self.logger.info(f"🔍 Обработка: {name}")
            self.logger.info(f"   URL: {url}")

            # Получение текущей цены
            price_data = self.parser.get_price(url, selectors)

            if not price_data or not price_data.get('price_found', False):
                self.logger.warning(f"⚠️ Не удалось получить цену для {name}")
                return None

            current_price = price_data['price']
            product_name = price_data.get('name', name)
            is_mock = price_data.get('is_mock', False)

            if is_mock:
                self.logger.info(f"🔄 Используются тестовые данные")

            self.logger.info(f"💰 Текущая цена: {current_price:.2f} {price_data.get('currency', 'RUB')}")

            # Получение последней цены из БД
            last_price = self.db.get_last_price(url)

            # Если цена изменилась, сохраняем в историю
            if last_price is None:
                self.db.save_price(url, current_price, product_name)
                self.logger.info(f"💾 Первое сохранение цены: {current_price:.2f}")
            elif abs(last_price - current_price) > 0.01:
                self.db.save_price(url, current_price, product_name)
                change = current_price - last_price
                change_percent = (change / last_price) * 100

                if change < 0:
                    self.logger.info(
                        f"📉 Цена снизилась: {last_price:.2f} -> {current_price:.2f} ({change_percent:+.2f}%)")
                else:
                    self.logger.info(
                        f"📈 Цена повысилась: {last_price:.2f} -> {current_price:.2f} ({change_percent:+.2f}%)")
            else:
                self.logger.info(f"⏸️ Цена не изменилась: {current_price:.2f}")

            # Проверка порога для уведомления
            if threshold and current_price < threshold:
                self.notifier.send_alert(
                    product_name=product_name,
                    current_price=current_price,
                    threshold=threshold,
                    url=url
                )
                self.logger.info(f"🔔 Уведомление: цена ниже порога ({current_price:.2f} < {threshold:.2f})")

            return {
                'url': url,
                'name': product_name,
                'price': current_price,
                'threshold': threshold,
                'currency': price_data.get('currency', 'RUB'),
                'is_mock': is_mock,
                'timestamp': datetime.now()
            }

        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки {name}: {e}")
            return None

    def run_once(self):
        """Однократный запуск мониторинга"""
        self.logger.info("=" * 60)
        self.logger.info("🔄 ЗАПУСК В РЕЖИМЕ ОДНОКРАТНОЙ ОБРАБОТКИ")
        self.logger.info("=" * 60)

        start_time = time.time()
        processed_count = 0
        success_count = 0
        mock_count = 0

        # Обработка всех URL из конфига
        for item in self.config.urls:
            result = self.process_product(item)

            if result:
                processed_count += 1
                if result.get('is_mock', False):
                    mock_count += 1
                else:
                    success_count += 1

            # Задержка между запросами
            if len(self.config.urls) > 1:
                time.sleep(self.config.request_delay)

        # Статистика обработки
        execution_time = time.time() - start_time

        self.logger.info("=" * 60)
        self.logger.info("📊 СТАТИСТИКА ОБРАБОТКИ")
        self.logger.info("=" * 60)
        self.logger.info(f"✅ Успешно обработано: {success_count}")
        self.logger.info(f"🔄 Тестовых данных: {mock_count}")
        self.logger.info(f"📦 Всего товаров: {processed_count}")
        self.logger.info(f"⏱️ Время выполнения: {execution_time:.2f} сек")

        # Отправка дневного отчета
        if processed_count > 0:
            self.logger.info("=" * 60)
            self.logger.info("📧 ГЕНЕРАЦИЯ ДНЕВНОГО ОТЧЕТА")

            report = self.reporter.generate_daily_report()
            if report:
                self.notifier.send_daily_report(report)
                self.logger.info("✅ Дневной отчет отправлен")

        # Запись в лог
        self.logger.info("=" * 60)
        self.logger.info(f"✅ ОБРАБОТКА ЗАВЕРШЕНА. Обработано товаров: {processed_count}")
        self.logger.info("=" * 60)

        return processed_count

    def run_daemon(self):
        """Запуск в режиме демона (бесконечный цикл)"""
        self.logger.info("=" * 60)
        self.logger.info(f"🔄 ЗАПУСК В РЕЖИМЕ ДЕМОНА")
        self.logger.info(f"⏱️ Интервал проверки: {self.config.check_interval} сек")
        self.logger.info("=" * 60)

        iteration = 1

        while self.running:
            try:
                self.logger.info("=" * 60)
                self.logger.info(f"📊 ИТЕРАЦИЯ #{iteration}")
                self.logger.info("=" * 60)

                iteration_start = time.time()

                processed = self.run_once()

                iteration_time = time.time() - iteration_start
                self.logger.info(f"⏱️ Итерация #{iteration} завершена за {iteration_time:.2f} сек")

                # Расчет времени до следующей итерации
                sleep_time = max(self.config.check_interval - iteration_time, 0)

                if sleep_time > 0:
                    self.logger.info(f"⏳ Ожидание {sleep_time:.2f} сек до следующей проверки")
                    self.logger.info("=" * 60)

                    # Постепенное ожидание с проверкой флага running
                    for _ in range(int(sleep_time)):
                        if not self.running:
                            break
                        time.sleep(1)

                iteration += 1

            except Exception as e:
                self.logger.error(f"❌ Критическая ошибка в цикле демона: {e}")
                self.logger.info("⏳ Пауза 60 сек перед повторной попыткой...")
                time.sleep(60)

        self.logger.info("🛑 Демон остановлен")


def main():
    """Точка входа в программу"""

    # Парсинг аргументов командной строки
    parser = argparse.ArgumentParser(
        description='📊 Система мониторинга цен (учебная версия)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python main.py --once              # Однократный запуск
  python main.py --daemon             # Запуск в режиме демона
  python main.py --once --config my_config.json  # Своим конфигом
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--once', action='store_true', help='Однократный запуск')
    group.add_argument('--daemon', action='store_true', help='Запуск в режиме демона')

    parser.add_argument('--config', type=str, default='config.json',
                        help='Путь к файлу конфигурации (по умолчанию: config.json)')

    args = parser.parse_args()

    print("""
╔══════════════════════════════════════════════════════════╗
║     📊 СИСТЕМА МОНИТОРИНГА ЦЕН (УЧЕБНАЯ ВЕРСИЯ)         ║
║     Для books.toscrape.com, quotes.toscrape.com         ║
╚══════════════════════════════════════════════════════════╝
    """)

    try:
        # Создание и запуск монитора
        monitor = PriceMonitor()

        if args.once:
            # Однократный запуск
            processed = monitor.run_once()
            if processed == 0:
                monitor.logger.error("❌ Не обработано ни одного товара")
                sys.exit(1)
            sys.exit(0)

        elif args.daemon:
            # Режим демона
            monitor.run_daemon()

    except KeyboardInterrupt:
        print("\n\n👋 Программа остановлена пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Необработанная ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()