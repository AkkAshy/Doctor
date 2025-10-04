from rest_framework import viewsets, permissions
from .models import GlucoseMeasurement, Event, Medication, StressNote, Reminder, MealPhoto
from .serializers import (
    GlucoseMeasurementSerializer, EventSerializer,
    MedicationSerializer, StressNoteSerializer,
    ReminderSerializer, MealPhotoSerializer
)


class IsOwnerOrDoctor(permissions.BasePermission):
    """
    Доступ:
    - Врач видит все записи
    - Пользователь видит только свои
    """
    def has_object_permission(self, request, view, obj):
        if hasattr(request.user, 'employee') and request.user.employee.role == 'doctor':
            return True
        return obj.employee.user == request.user

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class BaseEmployeeViewSet(viewsets.ModelViewSet):
    """
    Базовый класс: автоматически подставляет employee по request.user
    и ограничивает queryset только данными этого пользователя (если он не врач).
    """
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrDoctor]

    def perform_create(self, serializer):
        serializer.save(employee=self.request.user.employee)

    def get_queryset(self):
        qs = self.queryset
        user = self.request.user
        # ИСПРАВЛЕНО: правильная проверка роли врача
        if hasattr(user, 'employee') and user.employee.role == 'doctor':
            return qs  # врач видит всё
        return qs.filter(employee=user.employee)



class GlucoseMeasurementViewSet(BaseEmployeeViewSet):
    queryset = GlucoseMeasurement.objects.all()
    serializer_class = GlucoseMeasurementSerializer


class EventViewSet(BaseEmployeeViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer


class MealPhotoViewSet(BaseEmployeeViewSet):
    queryset = MealPhoto.objects.all()
    serializer_class = MealPhotoSerializer


class MedicationViewSet(BaseEmployeeViewSet):
    queryset = Medication.objects.all()
    serializer_class = MedicationSerializer


class StressNoteViewSet(BaseEmployeeViewSet):
    queryset = StressNote.objects.all()
    serializer_class = StressNoteSerializer


class ReminderViewSet(BaseEmployeeViewSet):
    queryset = Reminder.objects.all()
    serializer_class = ReminderSerializer
