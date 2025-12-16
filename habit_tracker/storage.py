import datetime
import json
import os
from pathlib import Path
from typing import List, Dict

class Storage:
    def __init__(self, filename: str):
        self.filename = filename
        self.load_data()

    def load_data(self):
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as f:
                self.data = json.load(f)
        else:
            self.data = {}

    def save_data(self):
        with open(self.filename, 'w') as f:
            json.dump(self.data, f, indent=4)

    def add_habit(self, user_id: int, habit_name: str):
        if str(user_id) not in self.data:
            self.data[str(user_id)] = {"habits": []}
        new_habit = {
            "id": len(self.data[str(user_id)]["habits"]) + 1,
            "name": habit_name,
            "created": datetime.now().strftime("%Y-%m-%d"),
            "history": [],
            "streak": 0
        }
        self.data[str(user_id)]["habits"].append(new_habit)
        self.save_data()

    def get_habits(self, user_id: int) -> List[Dict]:
        return self.data.get(str(user_id), {}).get("habits", [])

    def update_habit(self, user_id: int, updated_habit: Dict):
        habits = self.get_habits(user_id)
        for i, habit in enumerate(habits):
            if habit["id"] == updated_habit["id"]:
                habits[i] = updated_habit
                break
        self.save_data()

    def reset_habits(self, user_id: int):
        if str(user_id) in self.data:
            del self.data[str(user_id)]
            self.save_data()

    def get_all_users(self) -> List[int]:
        return [int(uid) for uid in self.data.keys()]