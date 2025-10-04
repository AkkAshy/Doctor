# authapp/tasks.py
import datetime
from django.utils import timezone
from django.conf import settings
from diary.models import GlucoseMeasurement, Event, Medication, StressNote
import logging
import json

logger = logging.getLogger(__name__)

# Ленивая инициализация OpenAI клиента
_openai_client = None

def get_openai_client():
    """Получить OpenAI клиент с проверкой API ключа"""
    global _openai_client
    
    if _openai_client is None:
        from openai import OpenAI
        import os
        
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
    Анализ данных пользователя за НЕДЕЛЮ с предсказанием тренда глюкозы на следующую неделю
    
    Возвращает словарь:
    {
        "analysis": "Текст анализа и рекомендаций от GPT",
        "chart_data": {
            "2025-10-06": 5.2,
            "2025-10-07": 5.5,
            "2025-10-08": 5.8,
            "2025-10-09": 5.6,
            "2025-10-10": 5.4,
            "2025-10-11": 5.3,
            "2025-10-12": 5.7
        }
    }
    """
    try:
        logger.info(f"=" * 50)
        logger.info(f"Starting comprehensive analysis for employee {employee.id} ({employee.user.username})")
        
        now = timezone.now()
        start_week = now - datetime.timedelta(days=7)  # ← ИЗМЕНЕНО: неделя вместо месяца
        
        logger.info(f"Date range: {start_week.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}")

        # 1. СОБИРАЕМ ВСЕ ДАННЫЕ ЗА НЕДЕЛЮ
        logger.info("Collecting data from database...")
        
        glucose_qs = GlucoseMeasurement.objects.filter(
            employee=employee,
            measured_at__gte=start_week
        ).order_by("measured_at")

        events_qs = Event.objects.filter(
            employee=employee,
            start_time__gte=start_week
        ).order_by("start_time")

        meds_qs = Medication.objects.filter(
            employee=employee,
            taken_at__gte=start_week
        ).order_by("taken_at")

        stress_qs = StressNote.objects.filter(
            employee=employee,
            noted_at__gte=start_week
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
            "date": g.measured_at.strftime("%Y-%m-%d"),
            "time": g.measured_at.strftime("%H:%M"),
            "value": float(g.value)
        } for g in glucose_qs]

        events_data = [{
            "date": e.start_time.strftime("%Y-%m-%d"),
            "time": e.start_time.strftime("%H:%M"),
            "type": e.type,
            "name": e.name,
            "desc": e.description,
            "calories": e.calories,
            "carbs": e.carbs,
            "sugars": e.sugars,
            "duration": e.duration,
            "steps": e.steps
        } for e in events_qs]

        meds_data = [{
            "date": m.taken_at.strftime("%Y-%m-%d"),
            "time": m.taken_at.strftime("%H:%M"),
            "name": m.name,
            "dosage": m.dose
        } for m in meds_qs]

        stress_data = [{
            "date": s.noted_at.strftime("%Y-%m-%d"),
            "time": s.noted_at.strftime("%H:%M"),
            "note": s.description
        } for s in stress_qs]

        logger.info(f"Data formatted successfully")

        # 3. ПРОВЕРКА НА НАЛИЧИЕ ДАННЫХ
        if not glucose_data and not events_data:
            logger.warning(f"Insufficient data for employee {employee.id} - no glucose or events found")
            
            # Генерируем пустой прогноз на неделю
            empty_forecast = {}
            for i in range(7):
                future_date = (now + datetime.timedelta(days=i+1)).strftime("%Y-%m-%d")
                empty_forecast[future_date] = None
            
            return {
                "analysis": (
                    "❌ Недостаточно данных за последнюю неделю для анализа.\n\n"
                    "Для получения персонализированных рекомендаций и прогноза добавьте:\n"
                    "• Измерения уровня глюкозы\n"
                    "• События (приёмы пищи, физическая активность)\n"
                    "• Информацию о принятых лекарствах\n"
                    "• Заметки о стрессе и самочувствии"
                ),
                "chart_data": empty_forecast
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

        # 5. ВЫЧИСЛЯЕМ СРЕДНИЕ ЗНАЧЕНИЯ ПО ДНЯМ
        from collections import defaultdict
        daily_glucose = defaultdict(list)
        for g in glucose_data:
            daily_glucose[g["date"]].append(g["value"])
        
        daily_averages = {
            date: round(sum(values) / len(values), 1)
            for date, values in daily_glucose.items()
        }
        
        logger.info(f"Daily averages calculated: {daily_averages}")

        # 6. ГЕНЕРИРУЕМ ДАТЫ ДЛЯ ПРОГНОЗА (следующие 7 дней)
        forecast_dates = []
        for i in range(7):
            future_date = (now + datetime.timedelta(days=i+1)).strftime("%Y-%m-%d")
            forecast_dates.append(future_date)
        
        logger.info(f"Forecast dates: {forecast_dates}")

        # 7. СОЗДАЁМ ПРОМПТ ДЛЯ OPENAI С ЗАПРОСОМ НА ПРОГНОЗ
        logger.info("Creating prompt for OpenAI...")
        
        prompt = f"""
                Проанализируй данные пользователя с диабетом за последние 7 дней и составь прогноз на следующую неделю:

                ДАННЫЕ ЗА ПРОШЕДШУЮ НЕДЕЛЮ:

                ГЛЮКОЗА (по дням):
                {json.dumps(daily_averages, ensure_ascii=False, indent=2)}

                ДЕТАЛЬНЫЕ ИЗМЕРЕНИЯ:
                {glucose_data if glucose_data else "данные отсутствуют"}

                СОБЫТИЯ (еда, активность):
                {events_data if events_data else "данные отсутствуют"}

                ЛЕКАРСТВА:
                {meds_data if meds_data else "данные отсутствуют"}

                СТРЕСС:
                {stress_data if stress_data else "данные отсутствуют"}

                {deviations_text}

                ЗАДАЧА:
                1. Проанализируй тренды и паттерны за неделю
                2. Дай персональные рекомендации
                3. ОБЯЗАТЕЛЬНО составь прогноз среднего уровня глюкозы на каждый из следующих 7 дней: {', '.join(forecast_dates)}

                ФОРМАТ ОТВЕТА:

                ## 📊 АНАЛИЗ ЗА НЕДЕЛЮ (100-150 слов)
                - Общая динамика уровня глюкозы
                - Средний уровень и диапазон колебаний
                - Выявленные паттерны (время суток, связь с едой/активностью)

                ## 🎯 ВЛИЯНИЕ ФАКТОРОВ (100-150 слов)
                - Как питание влияло на глюкозу
                - Влияние физической активности
                - Влияние стресса и лекарств

                ## 🔮 ПРОГНОЗ НА НЕДЕЛЮ (50-100 слов)
                - Ожидаемая динамика
                - Риски и на что обратить внимание
                - Рекомендации на основе прогноза

                ## 💡 ПЕРСОНАЛЬНЫЕ РЕКОМЕНДАЦИИ (150-200 слов)
                - Питание: конкретные продукты и время
                - Активность: типы, интенсивность, время
                - Режим дня и управление стрессом
                - Корректировка лекарств (если нужно)

                ## 📈 ПРОГНОЗ ГЛЮКОЗЫ (ОБЯЗАТЕЛЬНО!)
                Верни ТОЛЬКО JSON с прогнозом среднего уровня глюкозы на каждый день:
                ```json{{
                "{forecast_dates[0]}": 5.5,
                "{forecast_dates[1]}": 5.8,
                "{forecast_dates[2]}": 5.6,
                "{forecast_dates[3]}": 5.9,
                "{forecast_dates[4]}": 5.7,
                "{forecast_dates[5]}": 5.4,
                "{forecast_dates[6]}": 5.6
                }}

                ВАЖНО: 
                - Значения должны быть реалистичными (4-11 ммоль/л)
                - Учитывай выявленные тренды
                - Прогноз должен быть в отдельном JSON блоке
                - Используй эмодзи для наглядности
                - Максимум 500 слов для текста
                """

        logger.info(f"Prompt length: {len(prompt)} characters")

        # 8. ЗАПРОС К OPENAI
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
                            "Ты — медицинский помощник и эксперт по диабету с навыками прогнозирования. "
                            "Анализируй данные профессионально, давай конкретные рекомендации. "
                            "ОБЯЗАТЕЛЬНО включай JSON прогноз глюкозы на 7 дней в формате:\n"
                            '{"YYYY-MM-DD": число, ...}\n'
                            "Будь понятным и поддерживающим."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            logger.info("OpenAI API call completed successfully")
            
            full_response = response.choices[0].message.content.strip()
            logger.info(f"Full response length: {len(full_response)} characters")
            
        except Exception as openai_error:
            logger.error(f"OpenAI API error: {type(openai_error).__name__}")
            logger.error(f"Error details: {str(openai_error)}")
            raise

        # 9. ИЗВЛЕКАЕМ ПРОГНОЗ ИЗ ОТВЕТА
        logger.info("Extracting forecast from response...")
        
        forecast_data = {}
        analysis_text = full_response
        
        try:
            # Ищем JSON блок в ответе
            import re
            
            # Паттерны для поиска JSON
            patterns = [
                r'```json\s*(\{[^}]+\})\s*```',  # ```json {...} ```
                r'```\s*(\{[^}]+\})\s*```',      # ``` {...} ```
                r'\{["\']?\d{4}-\d{2}-\d{2}["\']?\s*:\s*\d+\.?\d*[^}]*\}',  # {"YYYY-MM-DD": число}
            ]
            
            json_match = None
            for pattern in patterns:
                json_match = re.search(pattern, full_response, re.DOTALL)
                if json_match:
                    break
            
            if json_match:
                json_str = json_match.group(1) if len(json_match.groups()) > 0 else json_match.group(0)
                json_str = json_str.strip()
                
                logger.info(f"Found JSON block: {json_str[:100]}...")
                
                # Парсим JSON
                forecast_data = json.loads(json_str)
                
                # Удаляем JSON блок из текста анализа
                analysis_text = full_response.replace(json_match.group(0), '').strip()
                
                logger.info(f"✅ Forecast extracted successfully: {forecast_data}")
            else:
                logger.warning("Could not find forecast JSON in response")
                
                # Генерируем дефолтный прогноз на основе средних значений
                if daily_averages:
                    avg_glucose = sum(daily_averages.values()) / len(daily_averages)
                else:
                    avg_glucose = 5.5
                
                for date in forecast_dates:
                    # Небольшие случайные колебания вокруг среднего
                    import random
                    variation = random.uniform(-0.5, 0.5)
                    forecast_data[date] = round(avg_glucose + variation, 1)
                
                logger.info(f"Generated default forecast: {forecast_data}")
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse forecast JSON: {e}")
            
            # Генерируем дефолтный прогноз
            if daily_averages:
                avg_glucose = sum(daily_averages.values()) / len(daily_averages)
            else:
                avg_glucose = 5.5
            
            for date in forecast_dates:
                forecast_data[date] = round(avg_glucose, 1)
            
            logger.info(f"Using default forecast due to parse error: {forecast_data}")
        
        except Exception as e:
            logger.error(f"Error extracting forecast: {e}", exc_info=True)
            
            # Дефолтный прогноз в случае ошибки
            for date in forecast_dates:
                forecast_data[date] = 5.5

        # 10. ВАЛИДАЦИЯ ПРОГНОЗА
        logger.info("Validating forecast data...")
        
        validated_forecast = {}
        for date in forecast_dates:
            if date in forecast_data:
                value = forecast_data[date]
                # Проверяем, что значение в разумных пределах (3-15 ммоль/л)
                if isinstance(value, (int, float)) and 3 <= value <= 15:
                    validated_forecast[date] = round(float(value), 1)
                else:
                    logger.warning(f"Invalid forecast value for {date}: {value}, using 5.5")
                    validated_forecast[date] = 5.5
            else:
                logger.warning(f"Missing forecast for {date}, using 5.5")
                validated_forecast[date] = 5.5
        
        logger.info(f"Validated forecast: {validated_forecast}")

        logger.info(f"✅ Comprehensive analysis completed successfully for employee {employee.id}")
        logger.info(f"=" * 50)

        # 11. ВОЗВРАЩАЕМ РЕЗУЛЬТАТ
        return {
            "analysis": analysis_text,
            "chart_data": validated_forecast
        }

    except Exception as e:
        logger.error(f"❌ CRITICAL ERROR in comprehensive analysis for employee {employee.id}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error(f"Full traceback:", exc_info=True)
        logger.error(f"=" * 50)
        
        # Генерируем дефолтный прогноз даже при ошибке
        now = timezone.now()
        error_forecast = {}
        for i in range(7):
            future_date = (now + datetime.timedelta(days=i+1)).strftime("%Y-%m-%d")
            error_forecast[future_date] = 5.5
        
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
            "chart_data": error_forecast
        }