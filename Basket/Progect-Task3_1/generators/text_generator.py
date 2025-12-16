import random
import json

TEMPLATES_PATH = "./templates/prompts.json"

def generate_text(type_, topic):
    with open(TEMPLATES_PATH, "r", encoding="utf-8") as f:
        templates = json.load(f)

    template = templates[type_][random.randint(0, len(templates[type_]) - 1)]
    prompt = template.format(topic=topic)

    # Здесь должен происходить реальный запрос к AI-модели
    generated_text = "AI-модель вернула текст..."
    return generated_text