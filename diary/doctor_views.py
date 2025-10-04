# diary/doctor_views.py
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework import serializers
from rest_framework.response import Response
from django.db.models import Q, Avg, Count, Max, Min
from django_filters.rest_framework import DjangoFilterBackend
from datetime import datetime, timedelta

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
        # Средний уровень глюкозы за последние 7 дней
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

class DoctorPatientViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для просмотра списка пациентов врачом
    
    Фильтры:
    - search: поиск по имени, фамилии, телефону
    - ordering: сортировка по created_at, full_name
    """
    serializer_class = DoctorPatientSerializer
    permission_classes = [IsDoctorPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__first_name', 'user__last_name', 'phone', 'user__username']
    ordering_fields = ['created_at', 'user__first_name', 'user__last_name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        # Только пациенты (role='user')
        return Employee.objects.filter(role='user').select_related('user')
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """
        Статистика по конкретному пациенту
        
        GET /api/doctor/patients/{id}/statistics/
        """
        patient = self.get_object()
        
        # Параметры для фильтрации по датам
        days = int(request.query_params.get('days', 30))
        date_from = datetime.now() - timedelta(days=days)
        
        # Статистика по глюкозе
        glucose_stats = patient.glucose_measurements.filter(
            measured_at__gte=date_from
        ).aggregate(
            avg=Avg('value'),
            max=Max('value'),
            min=Min('value'),
            count=Count('id')
        )
        
        # Статистика по событиям
        events_stats = {
            'total': patient.events.filter(start_time__gte=date_from).count(),
            'meals': patient.events.filter(type='meal', start_time__gte=date_from).count(),
            'walks': patient.events.filter(type='walk', start_time__gte=date_from).count(),
            'sports': patient.events.filter(type='sport', start_time__gte=date_from).count(),
        }
        
        # Статистика по лекарствам
        medications_stats = patient.medications.filter(
            taken_at__gte=date_from
        ).values('name').annotate(count=Count('id'))
        
        # Количество стресс-заметок
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


class DoctorGlucoseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для просмотра замеров глюкозы всех пациентов
    
    Фильтры:
    - employee: ID пациента
    - value_min: минимальное значение глюкозы
    - value_max: максимальное значение глюкозы
    - date_from: начальная дата (формат: YYYY-MM-DD)
    - date_to: конечная дата (формат: YYYY-MM-DD)
    - search: поиск по имени пациента
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
        
        # Фильтр по значению глюкозы
        value_min = self.request.query_params.get('value_min')
        value_max = self.request.query_params.get('value_max')
        
        if value_min:
            queryset = queryset.filter(value__gte=value_min)
        if value_max:
            queryset = queryset.filter(value__lte=value_max)
        
        # Фильтр по датам
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            queryset = queryset.filter(measured_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(measured_at__date__lte=date_to)
        
        return queryset


class DoctorEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для просмотра событий всех пациентов
    
    Фильтры:
    - employee: ID пациента
    - type: тип события (meal, walk, sport, other)
    - date_from: начальная дата
    - date_to: конечная дата
    - search: поиск по описанию и имени пациента
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
        
        # Фильтр по датам
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            queryset = queryset.filter(start_time__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(start_time__date__lte=date_to)
        
        return queryset


class DoctorMedicationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для просмотра лекарств всех пациентов
    
    Фильтры:
    - employee: ID пациента
    - name: название лекарства (частичное совпадение)
    - date_from: начальная дата
    - date_to: конечная дата
    - search: поиск по названию лекарства и имени пациента
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
        
        # Фильтр по названию лекарства
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__icontains=name)
        
        # Фильтр по датам
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            queryset = queryset.filter(taken_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(taken_at__date__lte=date_to)
        
        return queryset


class DoctorStressNoteViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для просмотра заметок о стрессе всех пациентов
    
    Фильтры:
    - employee: ID пациента
    - date_from: начальная дата
    - date_to: конечная дата
    - search: поиск по описанию и имени пациента
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
        
        # Фильтр по датам
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            queryset = queryset.filter(noted_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(noted_at__date__lte=date_to)
        
        return queryset


class DoctorDashboardViewSet(viewsets.ViewSet):
    """
    ViewSet для дашборда врача с общей статистикой
    """
    permission_classes = [IsDoctorPermission]
    
    def list(self, request):
        """
        Общая статистика по всем пациентам
        
        GET /api/doctor/dashboard/
        """
        days = int(request.query_params.get('days', 7))
        date_from = datetime.now() - timedelta(days=days)
        
        # Общее количество пациентов
        total_patients = Employee.objects.filter(role='user').count()
        
        # Пациенты с измерениями за период
        active_patients = Employee.objects.filter(
            role='user',
            glucose_measurements__measured_at__gte=date_from
        ).distinct().count()
        
        # Средний уровень глюкозы по всем пациентам
        avg_glucose = GlucoseMeasurement.objects.filter(
            measured_at__gte=date_from
        ).aggregate(Avg('value'))
        
        # Общее количество событий
        total_events = Event.objects.filter(start_time__gte=date_from).count()
        
        # Критические случаи (глюкоза > 10 или < 3)
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


# Добавьте этот импорт в начало файла
from rest_framework import serializers