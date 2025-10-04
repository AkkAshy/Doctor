import datetime
from django.utils import timezone
from django.conf import settings
from diary.models import GlucoseMeasurement, Event, Medication, StressNote
import logging

logger = logging.getLogger(__name__)

# Ленивая инициализация OpenAI клиента
_openai_client = None

def get_openai_client():
    """Получить OpenAI клиент с проверкой API ключа"""
    global _openai_client
    
    if _openai_client is None:
        from openai import OpenAI
        import os
        
        # Пробуем получить ключ разными способами
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key or api_key == "sk-proj-ваш-ключ":
            logger.error("OPENAI_API_KEY not found or is placeholder value")
            raise ValueError(
                "OPENAI_API_KEY не установлен. "
                "Добавьте его в .env файл или settings.py"
            )
        
        logger.info(f"Initializing OpenAI client with key: {api_key[:20]}...")
        _openai_client = OpenAI(api_key=api_key)
    
    return _openai_client


def get_comprehensive_analysis(employee):
    """
    Эпичная функция, которая делает всё сразу:
    - Собирает данные за 30 дней
    - Анализирует тренды с OpenAI
    - Генерирует рекомендации
    - Возвращает данные для графика

    Возвращает словарь:
    {
        "analysis": "Текст анализа и рекомендаций",
        "chart_data": {
            "labels": ["2025-09-04 10:00", ...],
            "glucose_values": [5.5, 6.2, ...],
            "normal_range": {"min": 4, "max": 11}
        }
    }
    """
    try:
        logger.info(f"=" * 50)
        logger.info(f"Starting comprehensive analysis for employee {employee.id} ({employee.user.username})")
        
        now = timezone.now()
        start_month = now - datetime.timedelta(days=30)
        
        logger.info(f"Date range: {start_month.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}")

        # 1. СОБИРАЕМ ВСЕ ДАННЫЕ ЗА МЕСЯЦ
        logger.info("Collecting data from database...")
        
        glucose_qs = GlucoseMeasurement.objects.filter(
            employee=employee,
            measured_at__gte=start_month
        ).order_by("measured_at")

        events_qs = Event.objects.filter(
            employee=employee,
            start_time__gte=start_month
        ).order_by("start_time")

        meds_qs = Medication.objects.filter(
            employee=employee,
            taken_at__gte=start_month
        ).order_by("taken_at")

        stress_qs = StressNote.objects.filter(
            employee=employee,
            noted_at__gte=start_month
        ).order_by("noted_at")

        glucose_count = glucose_qs.count()
        events_count = events_qs.count()
        meds_count = meds_qs.count()
        stress_count = stress_qs.count()
        
        logger.info(f"Data collected:")
        logger.info(f"  - Glucose measurements: {glucose_count}")
        logger.info(f"  - Events: {events_count}")
        logger.info(f"  - Medications: {meds_count}")
        logger.info(f"  - Stress notes: {stress_count}")

        # 2. ФОРМАТИРУЕМ ДАННЫЕ ДЛЯ АНАЛИЗА
        logger.info("Formatting data for analysis...")
        
        glucose_data = [{
            "time": g.measured_at.strftime("%Y-%m-%d %H:%M"),
            "value": float(g.value)
        } for g in glucose_qs]

        events_data = [{
            "time": e.start_time.strftime("%Y-%m-%d %H:%M"),
            "type": e.type,
            "desc": e.description,
            "calories": e.calories,
            "carbs": e.carbs,
            "sugars": e.sugars,
            "duration": e.duration,
            "steps": e.steps
        } for e in events_qs]

        meds_data = [{
            "time": m.taken_at.strftime("%Y-%m-%d %H:%M"),
            "name": m.name,
            "dosage": m.dose
        } for m in meds_qs]

        stress_data = [{
            "time": s.noted_at.strftime("%Y-%m-%d %H:%M"),
            "note": s.description
        } for s in stress_qs]

        logger.info(f"Data formatted successfully")

        # 3. ПРОВЕРКА НА НАЛИЧИЕ ДАННЫХ
        if not glucose_data and not events_data:
            logger.warning(f"Insufficient data for employee {employee.id} - no glucose or events found")
            return {
                "analysis": (
                    "❌ Недостаточно данных за последний месяц для анализа.\n\n"
                    "Для получения персонализированных рекомендаций добавьте:\n"
                    "• Измерения уровня глюкозы\n"
                    "• События (приёмы пищи, физическая активность)\n"
                    "• Информацию о принятых лекарствах\n"
                    "• Заметки о стрессе и самочувствии"
                ),
                "chart_data": {
                    "labels": [],
                    "glucose_values": [],
                    "normal_range": {"min": 4, "max": 11}
                }
            }

        # 4. АНАЛИЗ С ОТКЛОНЕНИЯМИ
        logger.info("Analyzing glucose deviations...")
        
        high_glucose = [g for g in glucose_data if g["value"] > 11]
        low_glucose = [g for g in glucose_data if g["value"] < 4]

        logger.info(f"  - High glucose cases (>11): {len(high_glucose)}")
        logger.info(f"  - Low glucose cases (<4): {len(low_glucose)}")

        deviations_text = ""
        if high_glucose:
            deviations_text += f"\n⚠️ Обнаружено {len(high_glucose)} случаев повышенного уровня глюкозы (>11 ммоль/л)."
        if low_glucose:
            deviations_text += f"\n⚠️ Обнаружено {len(low_glucose)} случаев пониженного уровня глюкозы (<4 ммоль/л)."

        # 5. СОЗДАЁМ ПРОМПТ ДЛЯ OPENAI
        logger.info("Creating prompt for OpenAI...")
        
        prompt = f"""
Проанализируй данные пользователя с диабетом за последние 30 дней:

ГЛЮКОЗА: {glucose_data if glucose_data else "данные отсутствуют"}

СОБЫТИЯ (еда, активность): {events_data if events_data else "данные отсутствуют"}

ЛЕКАРСТВА: {meds_data if meds_data else "данные отсутствуют"}

СТРЕСС: {stress_data if stress_data else "данные отсутствуют"}

{deviations_text}

Составь подробный анализ и рекомендации:

1. **ТРЕНДЫ ГЛЮКОЗЫ** (100-150 слов):
   - Общая динамика за месяц (стабильная/растущая/падающая)
   - Средний уровень и диапазон колебаний
   - Паттерны (время суток, дни недели)

2. **ВЛИЯНИЕ ФАКТОРОВ** (100-150 слов):
   - Как еда влияет на уровень глюкозы (углеводы, сахара)
   - Влияние физической активности (калории, шаги, длительность)
   - Влияние стресса и лекарств

3. **ПРОГНОЗ НА 7 ДНЕЙ** (50-100 слов):
   - Ожидаемая динамика на основе текущих трендов
   - Риски и на что обратить внимание

4. **ПЕРСОНАЛЬНЫЕ РЕКОМЕНДАЦИИ** (150-200 слов):
   - Питание: конкретные продукты и время приёма пищи
   - Активность: типы упражнений, интенсивность, время
   - Сон и стресс: методы релаксации, режим
   - Если есть отклонения глюкозы, дай конкретные действия

Если данных мало, укажи это и дай общие рекомендации для контроля диабета.
Ответ структурируй с заголовками, используй эмодзи для наглядности.
Максимум 500 слов.
"""

        logger.info(f"Prompt length: {len(prompt)} characters")

        # 6. ЗАПРОС К OPENAI
        logger.info("Calling OpenAI API...")
        
        try:
            client = get_openai_client()
            logger.info("OpenAI client initialized successfully")
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Ты — медицинский помощник и эксперт по диабету. "
                            "Анализируй данные профессионально, давай конкретные, "
                            "персонализированные рекомендации. Будь понятным и поддерживающим."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            logger.info("OpenAI API call completed successfully")
            
            analysis_text = response.choices[0].message.content.strip()
            logger.info(f"Analysis text length: {len(analysis_text)} characters")
            
        except Exception as openai_error:
            logger.error(f"OpenAI API error: {type(openai_error).__name__}")
            logger.error(f"Error details: {str(openai_error)}")
            raise

        # 7. ПОДГОТОВКА ДАННЫХ ДЛЯ ГРАФИКА
        logger.info("Preparing chart data...")
        
        chart_data = {
            "labels": [g["time"] for g in glucose_data],
            "glucose_values": [g["value"] for g in glucose_data],
            "normal_range": {"min": 4, "max": 11}
        }
        
        logger.info(f"Chart data prepared: {len(chart_data['labels'])} data points")

        logger.info(f"✅ Comprehensive analysis completed successfully for employee {employee.id}")
        logger.info(f"=" * 50)

        # 8. ВОЗВРАЩАЕМ РЕЗУЛЬТАТ
        return {
            "analysis": analysis_text,
            "chart_data": chart_data
        }

    except Exception as e:
        logger.error(f"❌ CRITICAL ERROR in comprehensive analysis for employee {employee.id}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error(f"Full traceback:", exc_info=True)
        logger.error(f"=" * 50)
        
        return {
            "analysis": (
                "❌ Произошла ошибка при анализе данных.\n\n"
                "Возможные причины:\n"
                "• Проблемы с подключением к OpenAI\n"
                "• Некорректные данные в базе\n"
                "• Технические неполадки\n\n"
                f"Тип ошибки: {type(e).__name__}\n"
                f"Детали: {str(e)}\n\n"
                "Попробуйте позже или обратитесь в поддержку."
            ),
            "chart_data": {
                "labels": [],
                "glucose_values": [],
                "normal_range": {"min": 4, "max": 11}
            }
        }