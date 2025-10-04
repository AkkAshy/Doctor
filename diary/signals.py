# app/signals.py
import base64
import requests
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import MealPhoto
from django.conf import settings


def analyze_food(image_path):
    with open(image_path, "rb") as f:
        img_bytes = f.read()
    b64_img = base64.b64encode(img_bytes).decode("utf-8")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Определи еду и оцени содержание сахара(г), ккал и углеводов. Верни JSON с food_name, sugars, kkal и carbohydrates."},
                    {"type": "image_url", "image_url": f"data:image/jpeg;base64,{b64_img}"}
                ]
            }
        ],
        "temperature": 0
    }

    resp = requests.post(url, headers=headers, json=payload)
    return resp.json()["choices"][0]["message"]["content"]


@receiver(post_save, sender=MealPhoto)
def process_meal_photo(sender, instance, created, **kwargs):
    if created and instance.image:
        try:
            result = analyze_food(instance.image.path)
            import json
            data = json.loads(result)

            instance.food_name = data.get("food_name")
            instance.sugars = data.get("sugars")
            instance.save(update_fields=["food_name", "sugars"])
        except Exception as e:
            print("Ошибка анализа фото:", e)
