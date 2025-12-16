import random
import json

TEMPLATES_PATH = "./templates/ideas.json"

def generate_ideas(topic):
    with open(TEMPLATES_PATH, "r", encoding="utf-8") as f:
        ideas = json.load(f)[topic]

    return random.sample(ideas, k=min(len(ideas), 10))  # Генерируем 10 случайных идей