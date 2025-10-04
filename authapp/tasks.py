import datetime
from django.utils import timezone
from openai import OpenAI
from diary.models import GlucoseMeasurement, Event, Medication, StressNote
import os

import logging

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)


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
        now = timezone.now()
        start_month = now - datetime.timedelta(days=30)

        # 1. СОБИРАЕМ ВСЕ ДАННЫЕ ЗА МЕСЯЦ
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

        # 2. ФОРМАТИРУЕМ ДАННЫЕ ДЛЯ АНАЛИЗА
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
            "dosage": m.dosage
        } for m in meds_qs]

        stress_data = [{
            "time": s.noted_at.strftime("%Y-%m-%d %H:%M"),
            "level": s.level,
            "note": s.note
        } for s in stress_qs]

        # 3. ПРОВЕРКА НА НАЛИЧИЕ ДАННЫХ
        if not glucose_data and not events_data:
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
        high_glucose = [g for g in glucose_data if g["value"] > 11]
        low_glucose = [g for g in glucose_data if g["value"] < 4]

        deviations_text = ""
        if high_glucose:
            deviations_text += f"\n⚠️ Обнаружено {len(high_glucose)} случаев повышенного уровня глюкозы (>11 ммоль/л)."
        if low_glucose:
            deviations_text += f"\n⚠️ Обнаружено {len(low_glucose)} случаев пониженного уровня глюкозы (<4 ммоль/л)."

        # 5. СОЗДАЁМ ПРОМПТ ДЛЯ OPENAI
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

        # 6. ЗАПРОС К OPENAI
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

        analysis_text = response.choices[0].message.content.strip()
        logger.info(f"Comprehensive analysis generated for employee {employee.id}")

        # 7. ПОДГОТОВКА ДАННЫХ ДЛЯ ГРАФИКА
        chart_data = {
            "labels": [g["time"] for g in glucose_data],
            "glucose_values": [g["value"] for g in glucose_data],
            "normal_range": {"min": 4, "max": 11}
        }

        # 8. ВОЗВРАЩАЕМ РЕЗУЛЬТАТ
        return {
            "analysis": analysis_text,
            "chart_data": chart_data
        }

    except Exception as e:
        logger.error(f"Error in comprehensive analysis for employee {employee.id}: {e}")
        return {
            "analysis": (
                "❌ Произошла ошибка при анализе данных.\n\n"
                "Возможные причины:\n"
                "• Проблемы с подключением к OpenAI\n"
                "• Некорректные данные в базе\n"
                "• Технические неполадки\n\n"
                "Попробуйте позже или обратитесь в поддержку."
            ),
            "chart_data": {
                "labels": [],
                "glucose_values": [],
                "normal_range": {"min": 4, "max": 11}
            }
        }


