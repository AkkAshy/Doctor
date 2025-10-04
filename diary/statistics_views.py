# diary/statistics_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from django.db.models import Min, Max
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Event, GlucoseMeasurement


@extend_schema(tags=['Статистика'])
class ActivityStatisticsView(APIView):
    """
    Статистика активности для графиков
    """
    permission_classes = [permissions.IsAuthenticated]
    
    ACTIVITY_CONFIG = {
        'meal': {'label': 'Приемы пищи', 'color': '#FF6B6B'},
        'walk': {'label': 'Прогулки', 'color': '#4ECDC4'},
        'sport': {'label': 'Спорт', 'color': '#95E1D3'},
        'other': {'label': 'Другое', 'color': '#A8E6CF'},
    }
    
    @extend_schema(
        summary="Статистика активности",
        description="""
        Возвращает статистику активности пользователя за выбранный период.
        
        Поддерживаемые периоды:
        - **month** (30 дней) - по умолчанию
        - **3months** (90 дней)
        - **6months** (180 дней)
        - **year** (365 дней)
        
        Можно фильтровать по типу активности.
        """,
        parameters=[
            OpenApiParameter(
                name='period',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Период: month, 3months, 6months, year',
                enum=['month', '3months', '6months', 'year']
            ),
            OpenApiParameter(
                name='type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Тип активности: meal, walk, sport, other',
                enum=['meal', 'walk', 'sport', 'other'],
                required=False
            )
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "period": {"type": "string", "example": "month"},
                    "days": {"type": "integer", "example": 30},
                    "data": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "label": {"type": "string"},
                                "color": {"type": "string"},
                                "points": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "date": {"type": "string", "format": "date"},
                                            "value": {"type": "integer"}
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "totals": {
                        "type": "object",
                        "properties": {
                            "meal": {"type": "integer"},
                            "walk": {"type": "integer"},
                            "sport": {"type": "integer"},
                            "steps": {"type": "integer"}
                        }
                    }
                }
            }
        }
    )
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
        points = []
        current_date = start_date.date()
        end = end_date.date()
        
        events_by_date = {}
        for event in queryset:
            date_key = event.start_time.date()
            if date_key not in events_by_date:
                events_by_date[date_key] = 0
            events_by_date[date_key] += 1
        
        while current_date <= end:
            points.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'value': events_by_date.get(current_date, 0)
            })
            current_date += timedelta(days=1)
        
        return points


@extend_schema(tags=['Статистика'])
class GlucoseStatisticsView(APIView):
    """
    Статистика уровня глюкозы
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Статистика глюкозы",
        description="""
        Возвращает статистику уровня глюкозы за выбранный период:
        
        - Временной ряд значений (среднее за день)
        - Средний уровень
        - Минимум и максимум
        - Количество измерений
        """,
        parameters=[
            OpenApiParameter(
                name='period',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Период: month, 3months, 6months, year',
                enum=['month', '3months', '6months', 'year']
            )
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "period": {"type": "string"},
                    "days": {"type": "integer"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "points": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "date": {"type": "string", "format": "date"},
                                        "value": {"type": "number"}
                                    }
                                }
                            },
                            "average": {"type": "number", "example": 5.8},
                            "min": {"type": "number", "example": 4.2},
                            "max": {"type": "number", "example": 9.5},
                            "measurements_count": {"type": "integer"}
                        }
                    }
                }
            }
        }
    )
    def get(self, request):
        employee = request.user.employee
        period = request.query_params.get('period', 'month')
        
        days_map = {'month': 30, '3months': 90, '6months': 180, 'year': 365}
        days = days_map.get(period, 30)
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        measurements = GlucoseMeasurement.objects.filter(
            employee=employee,
            measured_at__gte=start_date,
            measured_at__lte=end_date
        ).order_by('measured_at')
        
        points = self._group_by_date(measurements, start_date, end_date)
        
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
        from collections import defaultdict
        
        points = []
        current_date = start_date.date()
        end = end_date.date()
        
        measurements_by_date = defaultdict(list)
        for measurement in queryset:
            date_key = measurement.measured_at.date()
            measurements_by_date[date_key].append(measurement.value)
        
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


@extend_schema(tags=['Статистика'])
class NutritionStatisticsView(APIView):
    """
    Статистика питания (калории, углеводы, сахара)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    NUTRITION_CONFIG = {
        'calories': {'label': 'Калории (ккал)', 'color': '#FF6B6B', 'field': 'calories'},
        'carbs': {'label': 'Углеводы (г)', 'color': '#4ECDC4', 'field': 'carbs'},
        'sugars': {'label': 'Сахара (г)', 'color': '#FFD93D', 'field': 'sugars'},
    }
    
    @extend_schema(
        summary="Статистика питания",
        description="""
        Возвращает статистику питания за период:
        
        - Калории по дням
        - Углеводы по дням
        - Сахара по дням
        - Общие суммы
        """,
        parameters=[
            OpenApiParameter(
                name='period',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Период: month, 3months, 6months, year',
                enum=['month', '3months', '6months', 'year']
            )
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "period": {"type": "string"},
                    "days": {"type": "integer"},
                    "data": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "label": {"type": "string"},
                                "color": {"type": "string"},
                                "points": {"type": "array"}
                            }
                        }
                    },
                    "totals": {
                        "type": "object",
                        "properties": {
                            "calories": {"type": "number"},
                            "carbs": {"type": "number"},
                            "sugars": {"type": "number"}
                        }
                    }
                }
            }
        }
    )
    def get(self, request):
        employee = request.user.employee
        period = request.query_params.get('period', 'month')
        
        days_map = {'month': 30, '3months': 90, '6months': 180, 'year': 365}
        days = days_map.get(period, 30)
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        meals = Event.objects.filter(
            employee=employee,
            type='meal',
            start_time__gte=start_date,
            start_time__lte=end_date
        )
        
        data = []
        totals = {}
        
        for nutr_type, config in self.NUTRITION_CONFIG.items():
            field_name = config['field']
            
            points = self._group_by_date_nutrition(meals, start_date, end_date, field_name)
            
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
        from collections import defaultdict
        
        points = []
        current_date = start_date.date()
        end = end_date.date()
        
        values_by_date = defaultdict(float)
        for meal in queryset:
            date_key = meal.start_time.date()
            value = getattr(meal, field_name, 0) or 0
            values_by_date[date_key] += value
        
        while current_date <= end:
            value = values_by_date.get(current_date, 0)
            
            if value > 0:
                points.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'value': round(value, 2)
                })
            
            current_date += timedelta(days=1)
        
        return points