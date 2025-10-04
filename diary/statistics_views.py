# diary/statistics_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from django.db.models import Min, Max

from .models import Event, GlucoseMeasurement


class ActivityStatisticsView(APIView):
    """
    API для получения статистики активности пациента для графиков
    
    GET /api/diary/statistics/activity/
    
    Query Parameters:
    - period: month (по умолчанию), 3months, 6months, year
    - type: meal, walk, sport, other (опционально, для фильтрации по типу)
    
    Response:
    {
        "period": "month",
        "data": [
            {
                "type": "meal",
                "label": "Приемы пищи",
                "color": "#FF6B6B",
                "points": [
                    {"date": "2025-10-01", "value": 5},
                    {"date": "2025-10-02", "value": 4},
                    ...
                ]
            },
            {
                "type": "walk",
                "label": "Прогулки",
                "color": "#4ECDC4",
                "points": [...]
            },
            {
                "type": "sport",
                "label": "Спорт",
                "color": "#95E1D3",
                "points": [...]
            }
        ],
        "totals": {
            "meal": 122,
            "walk": 45,
            "sport": 28,
            "steps": 23448
        }
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    # Конфигурация типов активности
    ACTIVITY_CONFIG = {
        'meal': {'label': 'Приемы пищи', 'color': '#FF6B6B'},
        'walk': {'label': 'Прогулки', 'color': '#4ECDC4'},
        'sport': {'label': 'Спорт', 'color': '#95E1D3'},
        'other': {'label': 'Другое', 'color': '#A8E6CF'},
    }
    
    def get(self, request):
        employee = request.user.employee
        period = request.query_params.get('period', 'month')
        filter_type = request.query_params.get('type', None)

        days_map = {'month': 30, '3months': 90, '6months': 180, 'year': 365}
        days = days_map.get(period, 30)

        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        events = Event.objects.filter(
            employee=employee,
            start_time__gte=start_date,
            start_time__lte=end_date
        )

        if filter_type and filter_type in [t[0] for t in Event.EVENT_TYPES]:
            events = events.filter(type=filter_type)

        data = []
        totals = {'steps': 0}
        types_to_display = [filter_type] if filter_type else [t[0] for t in Event.EVENT_TYPES]

        for event_type in types_to_display:
            type_events = events.filter(type=event_type)
            if not type_events.exists():
                continue

            # Цвет берем из первого события типа
            color = type_events.first().color or '#CCCCCC'
            label = self.ACTIVITY_CONFIG.get(event_type, {}).get('label', event_type.title())
            points = self._group_by_date(type_events, start_date, end_date)

            total_count = type_events.count()
            totals[event_type] = total_count

            if event_type == 'walk':
                total_steps = type_events.aggregate(Sum('steps'))['steps__sum'] or 0
                totals['steps'] = int(total_steps)

            data.append({
                'type': event_type,
                'label': label,
                'color': color,
                'points': points
            })

        return Response({
            'period': period,
            'days': days,
            'data': data,
            'totals': totals
        })

    
    def _group_by_date(self, queryset, start_date, end_date):
        """
        Группирует события по датам и возвращает массив точек для графика
        """
        points = []
        current_date = start_date.date()
        end = end_date.date()
        
        # Создаем словарь для быстрого доступа
        events_by_date = {}
        for event in queryset:
            date_key = event.start_time.date()
            if date_key not in events_by_date:
                events_by_date[date_key] = 0
            events_by_date[date_key] += 1
        
        # Заполняем все дни периода
        while current_date <= end:
            points.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'value': events_by_date.get(current_date, 0)
            })
            current_date += timedelta(days=1)
        
        return points


class GlucoseStatisticsView(APIView):
    """
    API для получения статистики уровня глюкозы для графиков
    
    GET /api/diary/statistics/glucose/
    
    Query Parameters:
    - period: month (по умолчанию), 3months, 6months, year
    
    Response:
    {
        "period": "month",
        "data": {
            "points": [
                {"date": "2025-10-01", "value": 5.8},
                {"date": "2025-10-02", "value": 6.2},
                ...
            ],
            "average": 5.9,
            "min": 4.2,
            "max": 8.1,
            "measurements_count": 90
        }
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        employee = request.user.employee
        period = request.query_params.get('period', 'month')
        
        # Определяем период
        days_map = {
            'month': 30,
            '3months': 90,
            '6months': 180,
            'year': 365
        }
        days = days_map.get(period, 30)
        
        # Дата начала периода
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Получаем замеры за период
        measurements = GlucoseMeasurement.objects.filter(
            employee=employee,
            measured_at__gte=start_date,
            measured_at__lte=end_date
        ).order_by('measured_at')
        
        # Группируем по датам (берем среднее значение за день)
        points = self._group_by_date(measurements, start_date, end_date)
        
        # Статистика
        stats = measurements.aggregate(
            avg=Avg('value'),
            min=Min('value'),
            max=Max('value'),
            count=Count('id')
        )
        
        return Response({
            'period': period,
            'days': days,
            'data': {
                'points': points,
                'average': round(stats['avg'], 2) if stats['avg'] else None,
                'min': round(stats['min'], 2) if stats['min'] else None,
                'max': round(stats['max'], 2) if stats['max'] else None,
                'measurements_count': stats['count']
            }
        })
    
    def _group_by_date(self, queryset, start_date, end_date):
        """
        Группирует замеры по датам и возвращает среднее значение за день
        """
        from django.db.models import Avg
        from collections import defaultdict
        
        points = []
        current_date = start_date.date()
        end = end_date.date()
        
        # Группируем по датам
        measurements_by_date = defaultdict(list)
        for measurement in queryset:
            date_key = measurement.measured_at.date()
            measurements_by_date[date_key].append(measurement.value)
        
        # Заполняем все дни периода
        while current_date <= end:
            values = measurements_by_date.get(current_date, [])
            avg_value = sum(values) / len(values) if values else None
            
            if avg_value is not None:
                points.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'value': round(avg_value, 2)
                })
            
            current_date += timedelta(days=1)
        
        return points


class NutritionStatisticsView(APIView):
    """
    API для получения статистики питания (калории, углеводы, сахар)
    
    GET /api/diary/statistics/nutrition/
    
    Query Parameters:
    - period: month (по умолчанию), 3months, 6months, year
    
    Response:
    {
        "period": "month",
        "data": [
            {
                "type": "calories",
                "label": "Калории",
                "color": "#FF6B6B",
                "points": [
                    {"date": "2025-10-01", "value": 1850},
                    ...
                ]
            },
            {
                "type": "carbs",
                "label": "Углеводы",
                "color": "#4ECDC4",
                "points": [...]
            },
            {
                "type": "sugars",
                "label": "Сахара",
                "color": "#FFD93D",
                "points": [...]
            }
        ],
        "totals": {
            "calories": 55500,
            "carbs": 4200,
            "sugars": 780
        }
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    NUTRITION_CONFIG = {
        'calories': {'label': 'Калории (ккал)', 'color': '#FF6B6B', 'field': 'calories'},
        'carbs': {'label': 'Углеводы (г)', 'color': '#4ECDC4', 'field': 'carbs'},
        'sugars': {'label': 'Сахара (г)', 'color': '#FFD93D', 'field': 'sugars'},
    }
    
    def get(self, request):
        employee = request.user.employee
        period = request.query_params.get('period', 'month')
        
        # Определяем период
        days_map = {
            'month': 30,
            '3months': 90,
            '6months': 180,
            'year': 365
        }
        days = days_map.get(period, 30)
        
        # Дата начала периода
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Получаем только события типа meal
        meals = Event.objects.filter(
            employee=employee,
            type='meal',
            start_time__gte=start_date,
            start_time__lte=end_date
        )
        
        # Подготовка данных
        data = []
        totals = {}
        
        for nutr_type, config in self.NUTRITION_CONFIG.items():
            field_name = config['field']
            
            # Группируем по датам
            points = self._group_by_date_nutrition(meals, start_date, end_date, field_name)
            
            # Подсчитываем общую сумму
            total = meals.aggregate(Sum(field_name))[f'{field_name}__sum'] or 0
            totals[nutr_type] = round(total, 2)
            
            data.append({
                'type': nutr_type,
                'label': config['label'],
                'color': config['color'],
                'points': points
            })
        
        return Response({
            'period': period,
            'days': days,
            'data': data,
            'totals': totals
        })
    
    def _group_by_date_nutrition(self, queryset, start_date, end_date, field_name):
        """
        Группирует приемы пищи по датам и суммирует значения
        """
        from collections import defaultdict
        
        points = []
        current_date = start_date.date()
        end = end_date.date()
        
        # Группируем по датам
        values_by_date = defaultdict(float)
        for meal in queryset:
            date_key = meal.start_time.date()
            value = getattr(meal, field_name, 0) or 0
            values_by_date[date_key] += value
        
        # Заполняем все дни периода
        while current_date <= end:
            value = values_by_date.get(current_date, 0)
            
            if value > 0:
                points.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'value': round(value, 2)
                })
            
            current_date += timedelta(days=1)
        
        return points


