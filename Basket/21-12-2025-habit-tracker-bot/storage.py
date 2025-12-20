import json
import asyncio
from typing import Dict, Any, Optional
import aiofiles
from datetime import datetime
from cachetools import TTLCache
import config

class AsyncJSONStorage:
    """
    Асинхронное хранилище с кешированием для работы с JSON-файлом.
    Обеспечивает блокировки для предотвращения конфликтов при записи[citation:6].
    """
    _instance = None
    _lock = asyncio.Lock()  # Блокировка на уровне класса для операций записи

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_cache()
        return cls._instance

    def _init_cache(self):
        """Инициализация кеша в оперативной памяти (TTL 30 секунд)."""
        # Кешируем данные пользователя на 30 секунд
        self._cache = TTLCache(maxsize=100, ttl=30)
        self._file_path = config.DATA_FILE

    async def _read_file(self) -> Dict[str, Any]:
        """Чтение JSON-файла с обработкой ошибок[citation:2][citation:7]."""
        try:
            async with aiofiles.open(self._file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                if not content.strip():
                    return {}
                return json.loads(content)
        except FileNotFoundError:
            return {}  # Файл создастся при первой записи
        except json.JSONDecodeError as e:
            print(f"Ошибка чтения JSON: {e}. Создаю новый файл.")
            return {}

    async def _write_file(self, data: Dict[str, Any]):
        """Асинхронная запись данных в JSON-файл с красивым форматированием."""
        async with aiofiles.open(self._file_path, 'w', encoding='utf-8') as f:
            # Используем json.dumps с отступами для читаемости[citation:7]
            await f.write(json.dumps(data, indent=2, ensure_ascii=False))

    async def get_user_data(self, user_id: int) -> Dict[str, Any]:
        """Получение данных пользователя с использованием кеша."""
        # Пробуем получить из кеша
        cache_key = f"user_{user_id}"
        cached_data = self._cache.get(cache_key)
        if cached_data is not None:
            return cached_data

        # Читаем из файла
        all_data = await self._read_file()
        user_data = all_data.get(str(user_id), {
            "habits": [],
            "timezone": "Europe/Moscow",
            "created": datetime.now().strftime("%Y-%m-%d")
        })

        # Сохраняем в кеш
        self._cache[cache_key] = user_data
        return user_data

    async def save_user_data(self, user_id: int, user_data: Dict[str, Any]):
        """
        Сохранение данных пользователя с блокировкой для избежания конфликтов[citation:6].
        """
        async with self._lock:  # Важно: одна запись в момент времени
            # Получаем все данные
            all_data = await self._read_file()
            # Обновляем данные конкретного пользователя
            all_data[str(user_id)] = user_data

            # Записываем обратно
            await self._write_file(all_data)

            # Обновляем кеш
            cache_key = f"user_{user_id}"
            self._cache[cache_key] = user_data

    async def delete_user_data(self, user_id: int):
        """Удаление всех данных пользователя."""
        async with self._lock:
            all_data = await self._read_file()
            if str(user_id) in all_data:
                del all_data[str(user_id)]
                await self._write_file(all_data)

                # Удаляем из кеша
                cache_key = f"user_{user_id}"
                if cache_key in self._cache:
                    del self._cache[cache_key]