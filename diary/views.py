# diary/views.py

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from datetime import datetime

from .models import (
    GlucoseMeasurement, 
    Event, 
    Medication, 
    StressNote, 
    Reminder, 
    MealPhoto
)
from .serializers import (
    GlucoseMeasurementSerializer, 
    EventSerializer,
    MedicationSerializer, 
    StressNoteSerializer,
    ReminderSerializer, 
    MealPhotoSerializer,
    FoodAnalysisSerializer  # Добавим этот сериализатор
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
        if hasattr(user, 'employee') and user.employee.role == 'doctor':
            return qs  # врач видит всё
        return qs.filter(employee=user.employee)


class GlucoseMeasurementViewSet(BaseEmployeeViewSet):
    queryset = GlucoseMeasurement.objects.all()
    serializer_class = GlucoseMeasurementSerializer


class EventViewSet(BaseEmployeeViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    
    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def preview_meal(self, request):
        """
        Предпросмотр данных о еде по фото (БЕЗ сохранения)
        
        POST /api/diary/events/preview_meal/
        
        Form Data:
        - image: файл фото
        
        Response:
        {
            "success": true,
            "food_name": "Борщ",
            "calories": 320,
            "carbs": 25,
            "sugars": 8,
            "proteins": 18,
            "fats": 15,
            "description": "...",
            "confidence": "high",
            "suggested_event": {
                "type": "meal",
                "name": "Борщ",
                "calories": 320,
                "carbs": 25,
                "sugars": 8,
                "color": "#FF6B6B"
            }
        }
        """
        from .utils import analyze_food_image
        
        serializer = FoodAnalysisSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        image = serializer.validated_data['image']
        result = analyze_food_image(image)
        
        if not result.get('success'):
            return Response(
                {'error': result.get('error', 'Ошибка анализа')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Формируем предложение для создания события
        suggested_event = {
            'type': 'meal',
            'name': result['food_name'][:15],
            'description': result.get('description', ''),
            'calories': result['calories'],
            'carbs': result['carbs'],
            'sugars': result['sugars'],
            'color': '#FF6B6B'
        }
        
        return Response({
            **result,
            'suggested_event': suggested_event
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def create_meal_with_photo(self, request):
        """
        Создание события "еда" с автоанализом фото
        
        POST /api/diary/events/create_meal_with_photo/
        
        Form Data:
        - image: файл фото (обязательно)
        - description: описание (опционально)
        - start_time: время приема пищи (опционально)
        - name: название (опционально, будет взято из анализа)
        - calories: калории (опционально, будет взято из анализа)
        - carbs: углеводы (опционально)
        - sugars: сахара (опционально)
        
        Response:
        {
            "event": { событие },
            "analysis": { результат анализа },
            "photo_id": 123
        }
        """
        from .utils import analyze_food_image
        
        # Проверяем наличие фото
        if 'image' not in request.FILES:
            return Response(
                {'error': 'Фото обязательно для создания события типа "еда"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        image = request.FILES['image']
        
        # Анализируем фото
        analysis_result = analyze_food_image(image)
        
        if not analysis_result.get('success'):
            return Response(
                {'error': analysis_result.get('error', 'Ошибка анализа')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        employee = request.user.employee
        
        # Время приема пищи
        start_time = request.data.get('start_time')
        if start_time:
            try:
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except:
                start_time = timezone.now()
        else:
            start_time = timezone.now()
        
        # Создаем событие с данными из анализа или из формы
        event = Event.objects.create(
            employee=employee,
            type='meal',
            name=request.data.get('name') or analysis_result['food_name'][:15],
            description=request.data.get('description') or analysis_result.get('description', ''),
            calories=float(request.data.get('calories') or analysis_result['calories']),
            carbs=float(request.data.get('carbs') or analysis_result['carbs']),
            sugars=float(request.data.get('sugars') or analysis_result['sugars']),
            start_time=start_time,
            color='#FF6B6B'
        )
        
        # Сохраняем фото
        meal_photo = MealPhoto.objects.create(
            employee=employee,
            meal=event,
            image=image,
            food_name=analysis_result['food_name'],
            sugars=analysis_result['sugars']
        )
        
        return Response({
            'event': EventSerializer(event).data,
            'analysis': analysis_result,
            'photo_id': meal_photo.id
        }, status=status.HTTP_201_CREATED)


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


class FoodAnalysisViewSet(viewsets.ViewSet):
    """
    ViewSet для анализа фото еды
    
    POST /api/diary/food-analysis/analyze/
    - Загрузить фото
    - Получить результат анализа
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    @action(detail=False, methods=['post'])
    def analyze(self, request):
        """
        Анализ фото еды без сохранения в БД
        
        POST /api/diary/food-analysis/analyze/
        
        Form Data:
        - image: файл изображения
        
        Response:
        {
            "success": true,
            "food_name": "Гречка с курицей",
            "calories": 450,
            "carbs": 45,
            "sugars": 3,
            "proteins": 35,
            "fats": 15,
            "description": "Отварная гречневая каша с куриной грудкой",
            "confidence": "high",
            "portion_size": "350"
        }
        """
        from .utils import analyze_food_image
        
        serializer = FoodAnalysisSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        image = serializer.validated_data['image']
        
        # Анализируем фото
        result = analyze_food_image(image)
        
        if not result.get('success'):
            return Response(
                {'error': result.get('error', 'Ошибка анализа')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response(result, status=status.HTTP_200_OK)