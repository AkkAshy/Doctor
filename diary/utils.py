# diary/utils.py
import base64
import requests
from django.conf import settings
from PIL import Image
import io
import logging
import json

logger = logging.getLogger(__name__)


def analyze_food_image(image_file):
    """
    Анализирует фото еды через OpenAI Vision API
    
    Args:
        image_file: Django UploadedFile или путь к файлу
        
    Returns:
        dict: {
            'success': bool,
            'food_name': str,
            'calories': float,
            'carbs': float,
            'sugars': float,
            'proteins': float,
            'fats': float,
            'description': str,
            'confidence': str,
            'portion_size': str
        }
    """
    try:
        # Читаем файл и конвертируем в base64
        if hasattr(image_file, 'read'):
            image_file.seek(0)
            img_bytes = image_file.read()
        else:
            with open(image_file, "rb") as f:
                img_bytes = f.read()
        
        # Проверка и оптимизация размера
        img = Image.open(io.BytesIO(img_bytes))
        max_size = 2048
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            img_bytes = buffer.getvalue()
        
        b64_img = base64.b64encode(img_bytes).decode("utf-8")
        
        # Запрос к OpenAI
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Проанализируй это фото еды и верни ТОЛЬКО JSON без markdown форматирования:

{
  "food_name": "название блюда на русском",
  "calories": число_калорий,
  "carbs": граммы_углеводов,
  "sugars": граммы_сахара,
  "proteins": граммы_белков,
  "fats": граммы_жиров,
  "description": "краткое описание состава блюда",
  "confidence": "high/medium/low",
  "portion_size": "примерный размер порции в граммах"
}

Если не можешь точно определить - укажи приблизительные значения и confidence: "low"."""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64_img}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 500,
            "temperature": 0.3
        }
        
        logger.info("Отправка запроса к OpenAI Vision API...")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()
        
        # Убираем markdown форматирование
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
        
        logger.info(f"Получен ответ от OpenAI: {content[:200]}...")
        
        # Парсим JSON
        data = json.loads(content)
        
        logger.info(f"✅ Анализ завершен: {data.get('food_name')}")
        
        return {
            'success': True,
            'food_name': data.get('food_name', 'Неизвестно'),
            'calories': float(data.get('calories', 0)),
            'carbs': float(data.get('carbs', 0)),
            'sugars': float(data.get('sugars', 0)),
            'proteins': float(data.get('proteins', 0)),
            'fats': float(data.get('fats', 0)),
            'description': data.get('description', ''),
            'confidence': data.get('confidence', 'low'),
            'portion_size': data.get('portion_size', 'не определено')
        }
        
    except requests.exceptions.Timeout:
        logger.error("Timeout при обращении к OpenAI API")
        return {
            'success': False,
            'error': 'Превышено время ожидания ответа от сервера анализа'
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при обращении к OpenAI API: {e}")
        return {
            'success': False,
            'error': f'Ошибка связи с сервером: {str(e)}'
        }
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга JSON: {e}. Ответ: {content}")
        return {
            'success': False,
            'error': 'Не удалось распознать ответ от AI'
        }
    except Exception as e:
        logger.error(f"Неожиданная ошибка при анализе фото: {e}", exc_info=True)
        return {
            'success': False,
            'error': f'Ошибка анализа: {str(e)}'
        }