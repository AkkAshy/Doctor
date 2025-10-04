# diary/doctor_views.py
from rest_framework import viewsets, permissions, filters, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Avg, Count, Max, Min
from django_filters.rest_framework import DjangoFilterBackend
from datetime import datetime, timedelta
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from authapp.models import Employee
from .models import GlucoseMeasurement, Event, Medication, StressNote, Reminder, MealPhoto
from .serializers import (
    GlucoseMeasurementSerializer, EventSerializer,
    MedicationSerializer, StressNoteSerializer,
    ReminderSerializer, MealPhotoSerializer
)


class IsDoctorPermission(permissions.BasePermission):
    """
    Разрешение только для врачей
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'employee') and 
            request.user.employee.role == 'doctor'
        )


class DoctorPatientSerializer(serializers.ModelSerializer):
    """
    Сериализатор для отображения пациентов врачу
    """
    full_name = serializers.SerializerMethodField()
    last_glucose = serializers.SerializerMethodField()
    avg_glucose = serializers.SerializerMethodField()
    total_events = serializers.SerializerMethodField()
    
    class Meta:
        model = Employee
        fields = [
            'id', 'full_name', 'phone', 'created_at',
            'last_glucose', 'avg_glucose', 'total_events'
        ]
    
    def get_full_name(self, obj):
        return obj.user.get_full_name()
    
    def get_last_glucose(self, obj):
        last = obj.glucose_measurements.first()
        if last:
            return {
                'value': last.value,
                'measured_at': last.measured_at
            }
        return None
    
    def get_avg_glucose(self, obj):
        week_ago = datetime.now() - timedelta(days=7)
        avg = obj.glucose_measurements.filter(
            measured_at__gte=week_ago
        ).aggregate(Avg('value'))
        return round(avg['value__avg'], 2) if avg['value__avg'] else None
    
    def get_total_events(self, obj):
        return obj.events.count()


class DoctorGlucoseDetailSerializer(GlucoseMeasurementSerializer):
    """
    Расширенный сериализатор глюкозы для врача
    """
    patient_name = serializers.SerializerMethodField()
    patient_id = serializers.IntegerField(source='employee.id', read_only=True)
    
    class Meta(GlucoseMeasurementSerializer.Meta):
        fields = GlucoseMeasurementSerializer.Meta.fields + ['patient_name', 'patient_id']
    
    def get_patient_name(self, obj):
        return obj.employee.user.get_full_name()


class DoctorEventDetailSerializer(EventSerializer):
    """
    Расширенный сериализатор событий для врача
    """
    patient_name = serializers.SerializerMethodField()
    patient_id = serializers.IntegerField(source='employee.id', read_only=True)
    
    class Meta(EventSerializer.Meta):
        fields = EventSerializer.Meta.fields + ['patient_name', 'patient_id']
    
    def get_patient_name(self, obj):
        return obj.employee.user.get_full_name()


class DoctorMedicationDetailSerializer(MedicationSerializer):
    """
    Расширенный сериализатор лекарств для врача
    """
    patient_name = serializers.SerializerMethodField()
    patient_id = serializers.IntegerField(source='employee.id', read_only=True)
    
    class Meta(MedicationSerializer.Meta):
        fields = MedicationSerializer.Meta.fields + ['patient_name', 'patient_id']
    
    def get_patient_name(self, obj):
        return obj.employee.user.get_full_name()


class DoctorStressNoteDetailSerializer(StressNoteSerializer):
    """
    Расширенный сериализатор заметок о стрессе для врача
    """
    patient_name = serializers.SerializerMethodField()
    patient_id = serializers.IntegerField(source='employee.id', read_only=True)
    
    class Meta(StressNoteSerializer.Meta):
        fields = StressNoteSerializer.Meta.fields + ['patient_name', 'patient_id']
    
    def get_patient_name(self, obj):
        return obj.employee.user.get_full_name()


# ==================== ViewSets для врача ====================

@extend_schema(tags=['Врач - Пациенты'])
class DoctorPatientViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API для работы врача с пациентами
    """
    serializer_class = DoctorPatientSerializer
    permission_classes = [IsDoctorPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__first_name', 'user__last_name', 'phone', 'user__username']
    ordering_fields = ['created_at', 'user__first_name', 'user__last_name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Employee.objects.filter(role='user').select_related('user')
    
    @extend_schema(
        summary="Список пациентов",
        description="""
        Возвращает список всех пациентов врача.
        
        **Поддерживаемые фильтры:**
        - search: поиск по имени, фамилии, телефону, username
        - ordering: сортировка по created_at, user__first_name, user__last_name
        """,
        parameters=[
            OpenApiParameter('search', OpenApiTypes.STR, description='Поиск по имени/телефону'),
            OpenApiParameter('ordering', OpenApiTypes.STR, description='Сортировка')
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @extend_schema(
        summary="Детали пациента",
        description="Возвращает подробную информацию о конкретном пациенте"
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @extend_schema(
        summary="Статистика пациента",
        description="""
        Детальная статистика по пациенту за выбранный период:
        
        - Статистика по глюкозе (среднее, макс, мин)
        - Количество событий по типам
        - Статистика по лекарствам
        - Количество стресс-заметок
        """,
        parameters=[
            OpenApiParameter(
                'days',
                OpenApiTypes.INT,
                description='Количество дней для анализа (по умолчанию 30)',
                required=False
            )
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "patient": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "name": {"type": "string"},
                            "phone": {"type": "string"}
                        }
                    },
                    "period_days": {"type": "integer"},
                    "glucose": {
                        "type": "object",
                        "properties": {
                            "average": {"type": "number"},
                            "max": {"type": "number"},
                            "min": {"type": "number"},
                            "measurements_count": {"type": "integer"}
                        }
                    },
                    "events": {
                        "type": "object",
                        "properties": {
                            "total": {"type": "integer"},
                            "meals": {"type": "integer"},
                            "walks": {"type": "integer"},
                            "sports": {"type": "integer"}
                        }
                    },
                    "medications": {"type": "array"},
                    "stress_notes_count": {"type": "integer"}
                }
            }
        }
    )
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        patient = self.get_object()
        
        days = int(request.query_params.get('days', 30))
        date_from = datetime.now() - timedelta(days=days)
        
        glucose_stats = patient.glucose_measurements.filter(
            measured_at__gte=date_from
        ).aggregate(
            avg=Avg('value'),
            max=Max('value'),
            min=Min('value'),
            count=Count('id')
        )
        
        events_stats = {
            'total': patient.events.filter(start_time__gte=date_from).count(),
            'meals': patient.events.filter(type='meal', start_time__gte=date_from).count(),
            'walks': patient.events.filter(type='walk', start_time__gte=date_from).count(),
            'sports': patient.events.filter(type='sport', start_time__gte=date_from).count(),
        }
        
        medications_stats = patient.medications.filter(
            taken_at__gte=date_from
        ).values('name').annotate(count=Count('id'))
        
        stress_notes_count = patient.stress_notes.filter(
            noted_at__gte=date_from
        ).count()
        
        return Response({
            'patient': {
                'id': patient.id,
                'name': patient.user.get_full_name(),
                'phone': patient.phone
            },
            'period_days': days,
            'glucose': {
                'average': round(glucose_stats['avg'], 2) if glucose_stats['avg'] else None,
                'max': glucose_stats['max'],
                'min': glucose_stats['min'],
                'measurements_count': glucose_stats['count']
            },
            'events': events_stats,
            'medications': list(medications_stats),
            'stress_notes_count': stress_notes_count
        })


@extend_schema(tags=['Врач - Данные'])
class DoctorGlucoseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Просмотр замеров глюкозы всех пациентов
    """
    serializer_class = DoctorGlucoseDetailSerializer
    permission_classes = [IsDoctorPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee']
    search_fields = ['employee__user__first_name', 'employee__user__last_name']
    ordering_fields = ['measured_at', 'value']
    ordering = ['-measured_at']
    
    def get_queryset(self):
        queryset = GlucoseMeasurement.objects.all().select_related('employee__user')
        
        value_min = self.request.query_params.get('value_min')
        value_max = self.request.query_params.get('value_max')
        
        if value_min:
            queryset = queryset.filter(value__gte=value_min)
        if value_max:
            queryset = queryset.filter(value__lte=value_max)
        
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            queryset = queryset.filter(measured_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(measured_at__date__lte=date_to)
        
        return queryset
    
    @extend_schema(
        summary="Замеры глюкозы всех пациентов",
        description="""
        Список всех замеров глюкозы с фильтрацией.
        
        **Фильтры:**
        - employee: ID пациента
        - value_min: минимальное значение глюкозы
        - value_max: максимальное значение глюкозы
        - date_from: начальная дата (YYYY-MM-DD)
        - date_to: конечная дата (YYYY-MM-DD)
        - search: поиск по имени пациента
        """,
        parameters=[
            OpenApiParameter('employee', OpenApiTypes.INT, description='ID пациента'),
            OpenApiParameter('value_min', OpenApiTypes.NUMBER, description='Мин. уровень глюкозы'),
            OpenApiParameter('value_max', OpenApiTypes.NUMBER, description='Макс. уровень глюкозы'),
            OpenApiParameter('date_from', OpenApiTypes.DATE, description='Дата от'),
            OpenApiParameter('date_to', OpenApiTypes.DATE, description='Дата до'),
            OpenApiParameter('search', OpenApiTypes.STR, description='Поиск по имени'),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


@extend_schema(tags=['Врач - Данные'])
class DoctorEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Просмотр событий всех пациентов
    """
    serializer_class = DoctorEventDetailSerializer
    permission_classes = [IsDoctorPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee', 'type']
    search_fields = ['description', 'employee__user__first_name', 'employee__user__last_name']
    ordering_fields = ['start_time', 'type']
    ordering = ['-start_time']
    
    def get_queryset(self):
        queryset = Event.objects.all().select_related('employee__user').prefetch_related('photos')
        
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            queryset = queryset.filter(start_time__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(start_time__date__lte=date_to)
        
        return queryset
    
    @extend_schema(
        summary="События всех пациентов",
        description="""
        Список всех событий (еда, прогулки, спорт) с фильтрацией.
        
        **Фильтры:**
        - employee: ID пациента
        - type: тип события (meal, walk, sport, other)
        - date_from: начальная дата
        - date_to: конечная дата
        - search: поиск по описанию и имени
        """,
        parameters=[
            OpenApiParameter('employee', OpenApiTypes.INT),
            OpenApiParameter('type', OpenApiTypes.STR, enum=['meal', 'walk', 'sport', 'medicine', 'other']),
            OpenApiParameter('date_from', OpenApiTypes.DATE),
            OpenApiParameter('date_to', OpenApiTypes.DATE),
            OpenApiParameter('search', OpenApiTypes.STR),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


@extend_schema(tags=['Врач - Данные'])
class DoctorMedicationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Просмотр лекарств всех пациентов
    """
    serializer_class = DoctorMedicationDetailSerializer
    permission_classes = [IsDoctorPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee']
    search_fields = ['name', 'employee__user__first_name', 'employee__user__last_name']
    ordering_fields = ['taken_at', 'name']
    ordering = ['-taken_at']
    
    def get_queryset(self):
        queryset = Medication.objects.all().select_related('employee__user')
        
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__icontains=name)
        
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            queryset = queryset.filter(taken_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(taken_at__date__lte=date_to)
        
        return queryset
    
    @extend_schema(
        summary="Лекарства всех пациентов",
        parameters=[
            OpenApiParameter('employee', OpenApiTypes.INT),
            OpenApiParameter('name', OpenApiTypes.STR, description='Название лекарства'),
            OpenApiParameter('date_from', OpenApiTypes.DATE),
            OpenApiParameter('date_to', OpenApiTypes.DATE),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


@extend_schema(tags=['Врач - Данные'])
class DoctorStressNoteViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Просмотр заметок о стрессе всех пациентов
    """
    serializer_class = DoctorStressNoteDetailSerializer
    permission_classes = [IsDoctorPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee']
    search_fields = ['description', 'employee__user__first_name', 'employee__user__last_name']
    ordering_fields = ['noted_at']
    ordering = ['-noted_at']
    
    def get_queryset(self):
        queryset = StressNote.objects.all().select_related('employee__user')
        
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            queryset = queryset.filter(noted_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(noted_at__date__lte=date_to)
        
        return queryset
    
    @extend_schema(
        summary="Заметки о стрессе всех пациентов",
        parameters=[
            OpenApiParameter('employee', OpenApiTypes.INT),
            OpenApiParameter('date_from', OpenApiTypes.DATE),
            OpenApiParameter('date_to', OpenApiTypes.DATE),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


@extend_schema(tags=['Врач - Дашборд'])
class DoctorDashboardViewSet(viewsets.ViewSet):
    """
    Дашборд врача с общей статистикой
    """
    permission_classes = [IsDoctorPermission]
    
    @extend_schema(
        summary="Дашборд врача",
        description="""
        Общая статистика по всем пациентам:
        
        - Количество пациентов (всего и активных)
        - Средний уровень глюкозы
        - Общее количество событий
        - Критические случаи (высокая/низкая глюкоза)
        """,
        parameters=[
            OpenApiParameter(
                'days',
                OpenApiTypes.INT,
                description='Период анализа в днях (по умолчанию 7)',
                required=False
            )
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "period_days": {"type": "integer"},
                    "total_patients": {"type": "integer"},
                    "active_patients": {"type": "integer"},
                    "avg_glucose": {"type": "number"},
                    "total_events": {"type": "integer"},
                    "critical_cases": {
                        "type": "object",
                        "properties": {
                            "high_glucose": {"type": "array"},
                            "low_glucose": {"type": "array"}
                        }
                    }
                }
            }
        }
    )
    def list(self, request):
        days = int(request.query_params.get('days', 7))
        date_from = datetime.now() - timedelta(days=days)
        
        total_patients = Employee.objects.filter(role='user').count()
        
        active_patients = Employee.objects.filter(
            role='user',
            glucose_measurements__measured_at__gte=date_from
        ).distinct().count()
        
        avg_glucose = GlucoseMeasurement.objects.filter(
            measured_at__gte=date_from
        ).aggregate(Avg('value'))
        
        total_events = Event.objects.filter(start_time__gte=date_from).count()
        
        critical_high = GlucoseMeasurement.objects.filter(
            measured_at__gte=date_from,
            value__gt=10
        ).select_related('employee__user').order_by('-measured_at')[:10]
        
        critical_low = GlucoseMeasurement.objects.filter(
            measured_at__gte=date_from,
            value__lt=3
        ).select_related('employee__user').order_by('-measured_at')[:10]
        
        return Response({
            'period_days': days,
            'total_patients': total_patients,
            'active_patients': active_patients,
            'avg_glucose': round(avg_glucose['value__avg'], 2) if avg_glucose['value__avg'] else None,
            'total_events': total_events,
            'critical_cases': {
                'high_glucose': [
                    {
                        'patient': m.employee.user.get_full_name(),
                        'patient_id': m.employee.id,
                        'value': m.value,
                        'measured_at': m.measured_at
                    } for m in critical_high
                ],
                'low_glucose': [
                    {
                        'patient': m.employee.user.get_full_name(),
                        'patient_id': m.employee.id,
                        'value': m.value,
                        'measured_at': m.measured_at
                    } for m in critical_low
                ]
            }
        })