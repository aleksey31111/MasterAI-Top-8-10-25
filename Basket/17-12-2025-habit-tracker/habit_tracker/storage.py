import json
from pathlib import Path
from typing import Dict, List


class HabitStorage:
    def __init__(self, filename="habits.json"):
        self.filename = filename
        self.cache = {}
        self.load()

    async def load(self):
        try:
            with open(self.filename, mode='r', encoding='utf-8') as f:
                data = json.load(f)
                for user_id, info in data.items():
                    self.cache[user_id] = info
        except FileNotFoundError:
            pass

    async def save(self):
        with open(self.filename, mode='w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=4)

    async def add_user(self, user_id: str, timezone: str):
        if user_id not in self.cache:
            self.cache[user_id] = {"habits": [], "timezone": timezone}
            await self.save()

    async def get_user_data(self, user_id: str) -> dict:
        return self.cache.get(user_id, {})

    async def set_user_data(self, user_id: str, data: dict):
        self.cache[user_id] = data
        await self.save()

    async def update_habit(self, user_id: str, habit_id: int, updates: dict):
        user_data = await self.get_user_data(user_id)
        for i, habit in enumerate(user_data["habits"]):
            if habit["id"] == habit_id:
                updated_habit = {**habit, **updates}
                user_data["habits"][i] = updated_habit
                break
        await self.set_user_data(user_id, user_data)

    async def delete_habit(self, user_id: str, habit_id: int):
        user_data = await self.get_user_data(user_id)
        user_data["habits"] = [h for h in user_data["habits"] if h["id"] != habit_id]
        await self.set_user_data(user_id, user_data)

    async def reset_all_habits(self, user_id: str):
        user_data = await self.get_user_data(user_id)
        user_data["habits"] = []
        await self.set_user_data(user_id, user_data)