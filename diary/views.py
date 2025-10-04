# diary/views.py

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from datetime import datetime
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

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
    FoodAnalysisSerializer
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
            return qs
        return qs.filter(employee=user.employee)


@extend_schema(tags=['Дневник - Глюкоза'])
class GlucoseMeasurementViewSet(BaseEmployeeViewSet):
    """
    CRUD для измерений уровня глюкозы
    """
    queryset = GlucoseMeasurement.objects.all()
    serializer_class = GlucoseMeasurementSerializer

    @extend_schema(
        summary="Список измерений глюкозы",
        description="Возвращает список всех измерений уровня глюкозы текущего пользователя"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Добавить измерение глюкозы",
        description="Создает новое измерение уровня глюкозы",
        examples=[
            OpenApiExample(
                "Пример создания",
                value={"value": 5.8},
                request_only=True
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Получить измерение",
        description="Возвращает конкретное измерение по ID"
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Обновить измерение",
        description="Обновляет существующее измерение"
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Удалить измерение",
        description="Удаляет измерение глюкозы"
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


@extend_schema(tags=['Дневник - События'])
class EventViewSet(BaseEmployeeViewSet):
    """
    CRUD для событий (еда, прогулки, спорт)
    """
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    
    @extend_schema(
        summary="Список событий",
        description="Возвращает все события пользователя (еда, прогулки, спорт и т.д.)"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Создать событие",
        description="""
        Создает новое событие. Поддерживаемые типы:
        - **meal** - прием пищи
        - **walk** - прогулка
        - **sport** - спортивная активность
        - **medicine** - прием лекарств
        - **other** - другое
        """,
        examples=[
            OpenApiExample(
                "Прием пищи",
                value={
                    "type": "meal",
                    "name": "Обед",
                    "description": "Гречка с курицей",
                    "calories": 450,
                    "carbs": 45,
                    "sugars": 3,
                    "start_time": "2025-10-05T13:00:00Z",
                    "color": "#FF6B6B"
                },
                request_only=True
            ),
            OpenApiExample(
                "Прогулка",
                value={
                    "type": "walk",
                    "name": "Вечерняя прогулка",
                    "duration": 30,
                    "steps": 4000,
                    "start_time": "2025-10-05T18:00:00Z",
                    "color": "#4ECDC4"
                },
                request_only=True
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @extend_schema(
        summary="Предпросмотр еды по фото",
        description="""
        **AI Анализ фото еды** - загрузите фото и получите данные БЕЗ сохранения в БД:
        
        - Название блюда
        - Калории, углеводы, сахара
        - Белки и жиры
        - Описание состава
        - Уверенность AI (high/medium/low)
        
        **Использует GPT-4 Vision API**, поэтому запрос может занять 5-10 секунд.
        """,
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'image': {'type': 'string', 'format': 'binary'}
                }
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "food_name": {"type": "string", "example": "Борщ"},
                    "calories": {"type": "number", "example": 320},
                    "carbs": {"type": "number", "example": 25},
                    "sugars": {"type": "number", "example": 8},
                    "proteins": {"type": "number", "example": 18},
                    "fats": {"type": "number", "example": 15},
                    "description": {"type": "string"},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                    "suggested_event": {
                        "type": "object",
                        "description": "Готовый объект для создания события"
                    }
                }
            },
            400: {"description": "Ошибка валидации файла"},
            500: {"description": "Ошибка анализа AI"}
        }
    )
    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def preview_meal(self, request):
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
    
    @extend_schema(
        summary="Создать событие 'еда' с фото",
        description="""
        **Создание приема пищи с автоматическим AI анализом фото**
        
        Процесс:
        1. Загружаете фото
        2. AI анализирует состав
        3. Автоматически создается событие с данными
        4. Фото сохраняется и привязывается к событию
        
        Параметры можно переопределить вручную.
        """,
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'image': {'type': 'string', 'format': 'binary', 'description': 'Фото еды (обязательно)'},
                    'description': {'type': 'string'},
                    'start_time': {'type': 'string', 'format': 'date-time'},
                    'name': {'type': 'string'},
                    'calories': {'type': 'number'},
                    'carbs': {'type': 'number'},
                    'sugars': {'type': 'number'}
                },
                'required': ['image']
            }
        },
        responses={
            201: {
                "type": "object",
                "properties": {
                    "event": {"type": "object", "description": "Созданное событие"},
                    "analysis": {"type": "object", "description": "Результат AI анализа"},
                    "photo_id": {"type": "integer", "description": "ID сохраненного фото"}
                }
            }
        }
    )
    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def create_meal_with_photo(self, request):
        from .utils import analyze_food_image
        
        if 'image' not in request.FILES:
            return Response(
                {'error': 'Фото обязательно для создания события типа "еда"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        image = request.FILES['image']
        analysis_result = analyze_food_image(image)
        
        if not analysis_result.get('success'):
            return Response(
                {'error': analysis_result.get('error', 'Ошибка анализа')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        employee = request.user.employee
        
        start_time = request.data.get('start_time')
        if start_time:
            try:
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except:
                start_time = timezone.now()
        else:
            start_time = timezone.now()
        
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


@extend_schema(tags=['Дневник - Фото еды'])
class MealPhotoViewSet(BaseEmployeeViewSet):
    """
    Управление фотографиями еды
    """
    queryset = MealPhoto.objects.all()
    serializer_class = MealPhotoSerializer

    @extend_schema(summary="Список фото еды")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(summary="Загрузить фото еды")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


@extend_schema(tags=['Дневник - Лекарства'])
class MedicationViewSet(BaseEmployeeViewSet):
    """
    CRUD для приема лекарств
    """
    queryset = Medication.objects.all()
    serializer_class = MedicationSerializer

    @extend_schema(
        summary="Список лекарств",
        description="Возвращает историю приема лекарств"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Добавить прием лекарства",
        examples=[
            OpenApiExample(
                "Пример",
                value={
                    "name": "Инсулин",
                    "dose": "10 ед.",
                    "taken_at": "2025-10-05T08:00:00Z"
                },
                request_only=True
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


@extend_schema(tags=['Дневник - Стресс'])
class StressNoteViewSet(BaseEmployeeViewSet):
    """
    Заметки о стрессе и самочувствии
    """
    queryset = StressNote.objects.all()
    serializer_class = StressNoteSerializer

    @extend_schema(summary="Список заметок о стрессе")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Добавить заметку о стрессе",
        examples=[
            OpenApiExample(
                "Пример",
                value={"description": "Сегодня был тяжелый день на работе, чувствую усталость"},
                request_only=True
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


@extend_schema(tags=['Дневник - Напоминания'])
class ReminderViewSet(BaseEmployeeViewSet):
    """
    Напоминания для пользователя
    """
    queryset = Reminder.objects.all()
    serializer_class = ReminderSerializer

    @extend_schema(summary="Список напоминаний")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Создать напоминание",
        examples=[
            OpenApiExample(
                "Пример",
                value={
                    "text": "Измерить глюкозу",
                    "remind_at": "2025-10-05T20:00:00Z"
                },
                request_only=True
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)