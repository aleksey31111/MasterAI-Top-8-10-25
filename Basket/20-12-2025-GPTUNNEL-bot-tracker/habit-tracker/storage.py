import json
import asyncio
import aiofiles
from datetime import datetime, date
import os


class HabitStorage:
    def __init__(self, filename):
        self.filename = filename
        self.cache = {}
        self.lock = asyncio.Lock()

    async def _load_data(self):
        if os.path.exists(self.filename):
            async with self.lock, aiofiles.open(self.filename, 'r') as f:
                return json.loads(await f.read())
        return {}

    async def _save_data(self, data):
        async with self.lock, aiofiles.open(self.filename, 'w') as f:
            await f.write(json.dumps(data, indent=2, ensure_ascii=False))

    async def init_user(self, user_id):
        data = await self._load_data()
        if str(user_id) not in data:
            data[str(user_id)] = {
                'habits': [],
                'timezone': 'Europe/Moscow'
            }
            await self._save_data(data)
            self.cache = data

    async def get_user_data(self, user_id):
        if not self.cache:
            self.cache = await self._load_data()
        return self.cache.get(str(user_id), {'habits': [], 'timezone': 'Europe/Moscow'})

    async def get_habits(self, user_id):
        user_data = await self.get_user_data(user_id)
        return user_data['habits']

    async def get_habit(self, user_id, habit_id):
        habits = await self.get_habits(user_id)
        for habit in habits:
            if habit['id'] == habit_id:
                return habit
        return None

    async def add_habit(self, user_id, name):
        data = await self._load_data()
        user_key = str(user_id)

        if user_key not in data:
            data[user_key] = {'habits': [], 'timezone': 'Europe/Moscow'}

        habit_id = len(data[user_key]['habits']) + 1
        new_habit = {
            'id': habit_id,
            'name': name,
            'created': date.today().isoformat(),
            'history': [],
            'streak': 0
        }

        data[user_key]['habits'].append(new_habit)
        await self._save_data(data)
        self.cache = data
        return habit_id

    async def check_habit(self, user_id, habit_id):
        data = await self._load_data()
        user_key = str(user_id)

        if user_key not in data:
            return False

        today = date.today().isoformat()
        for habit in data[user_key]['habits']:
            if habit['id'] == habit_id:
                if today not in habit['history']:
                    habit['history'].append(today)
                    # Update streak
                    yesterday = (date.today() - date.resolution).isoformat()
                    if yesterday in habit['history']:
                        habit['streak'] += 1
                    else:
                        habit['streak'] = 1
                await self._save_data(data)
                self.cache = data
                return True
        return False

    async def reset_user(self, user_id):
        data = await self._load_data()
        user_key = str(user_id)

        if user_key in data:
            data[user_key]['habits'] = []
            await self._save_data(data)
            self.cache = data
            return True
        return False
