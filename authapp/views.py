# auth/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from .models import Employee, TelegramAuthCode, HealthRecommendation
from .serializers import UserSerializer, HealthRecommendationSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from .tasks import get_comprehensive_analysis
import logging

logger = logging.getLogger(__name__)


class HealthRecommendationView(APIView):
    """
    Генерация персонализированных рекомендаций с AI анализом
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['AI Рекомендации'],
        summary="Получить AI рекомендации",
        description="""
        Генерирует персонализированные рекомендации на основе данных пользователя за последнюю неделю:
        
        - Анализ уровня глюкозы
        - Влияние питания и активности
        - Прогноз на следующую неделю
        - Персональные советы
        
        **ВАЖНО**: Анализ использует OpenAI GPT-4, поэтому запрос может занять 5-15 секунд.
        """,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "analysis": {
                        "type": "string",
                        "description": "Текстовый анализ и рекомендации от AI"
                    },
                    "chart_data": {
                        "type": "object",
                        "description": "Прогноз глюкозы на 7 дней",
                        "example": {
                            "2025-10-06": 5.2,
                            "2025-10-07": 5.5,
                            "2025-10-08": 5.8
                        }
                    }
                }
            },
            404: {"description": "Профиль сотрудника не найден"},
            500: {"description": "Ошибка генерации анализа"}
        }
    )
    def get(self, request):
        employee = getattr(request.user, "employee", None)
        if not employee:
            return Response(
                {"error": "Профиль сотрудника не найден"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            result = get_comprehensive_analysis(employee)
            return Response({
                "analysis": result["analysis"],
                "chart_data": result["chart_data"]
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return Response(
                {"error": "Ошибка при генерации анализа", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RegisterView(APIView):
    """
    Регистрация нового пользователя
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Авторизация'],
        summary="Регистрация пользователя",
        description="Создает нового пользователя с профилем Employee и возвращает JWT токены",
        request=UserSerializer,
        responses={
            201: {
                "type": "object",
                "properties": {
                    "refresh": {"type": "string", "description": "JWT Refresh Token"},
                    "access": {"type": "string", "description": "JWT Access Token"},
                    "user": {"type": "object", "description": "Данные пользователя"}
                }
            },
            400: {"description": "Ошибка валидации данных"}
        },
        examples=[
            OpenApiExample(
                "Пример регистрации",
                value={
                    "username": "ivan_petrov",
                    "email": "ivan@example.com",
                    "password": "SecurePass123",
                    "first_name": "Иван",
                    "last_name": "Петров",
                    "employee": {
                        "role": "user",
                        "phone": "+998901234567"
                    }
                },
                request_only=True
            )
        ]
    )
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TelegramProfileView(APIView):
    """
    Получение профиля по Telegram ID
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Telegram'],
        summary="Получить профиль по Telegram ID",
        description="Возвращает профиль пользователя, привязанный к указанному Telegram ID",
        parameters=[
            OpenApiParameter(
                name='telegram_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='Telegram ID пользователя'
            )
        ],
        responses={
            200: UserSerializer,
            404: {"description": "Профиль не найден"}
        }
    )
    def get(self, request, telegram_id):
        try:
            employee = Employee.objects.select_related("user").get(telegram_id=telegram_id)
            serializer = UserSerializer(employee.user)
            return Response(serializer.data)
        except Employee.DoesNotExist:
            return Response({"error": "Профиль не найден"}, status=404)


class GetProfileView(APIView):
    """
    Получение данных текущего пользователя
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Авторизация'],
        summary="Мой профиль",
        description="Возвращает данные авторизованного пользователя",
        responses={200: UserSerializer}
    )
    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data)


class ProfileUpdateView(APIView):
    """
    Обновление профиля пользователя
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Авторизация'],
        summary="Обновить профиль",
        description="Обновляет данные профиля текущего пользователя",
        request=UserSerializer,
        responses={
            200: UserSerializer,
            400: {"description": "Ошибка валидации"}
        }
    )
    def put(self, request):
        user = request.user
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GenerateTelegramCodeView(APIView):
    """
    Генерация кода для привязки Telegram
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Telegram'],
        summary="Сгенерировать код для Telegram",
        description="""
        Генерирует уникальный код для привязки аккаунта к Telegram боту.
        
        Код действителен 30 минут.
        """,
        responses={
            201: {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "example": "ABC123"},
                    "link": {"type": "string", "example": "https://t.me/Gluzone_Bot?start=ABC123"}
                }
            },
            500: {"description": "Бот не настроен на сервере"}
        }
    )
    def get(self, request):
        from django.conf import settings

        user = request.user
        code = TelegramAuthCode.generate_for_user(user)

        bot_username = getattr(settings, "TELEGRAM_BOT_USERNAME", None)
        if not bot_username:
            return Response({"error": "Бот не настроен на сервере"}, status=500)

        link = f"https://t.me/{bot_username}?start={code}"

        return Response({
            "code": code,
            "link": link,
        }, status=status.HTTP_201_CREATED)


class ConfirmTelegramCodeView(APIView):
    """
    Подтверждение кода и привязка Telegram
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Telegram'],
        summary="Подтвердить код Telegram",
        description="Привязывает Telegram ID к аккаунту пользователя и возвращает JWT токены",
        request={
            "type": "object",
            "properties": {
                "code": {"type": "string", "example": "ABC123"},
                "telegram_id": {"type": "string", "example": "123456789"}
            },
            "required": ["code", "telegram_id"]
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "access": {"type": "string"},
                    "refresh": {"type": "string"},
                    "user": {"type": "object"}
                }
            },
            400: {"description": "Неверный или просроченный код"}
        }
    )
    def post(self, request):
        code = request.data.get("code")
        telegram_id = request.data.get("telegram_id")

        if not code or not telegram_id:
            return Response({"error": "Не указан код или telegram_id"}, status=400)

        user = TelegramAuthCode.verify_code(code)
        if not user:
            return Response({"error": "Неверный или просроченный код"}, status=400)

        # Привязываем Telegram ID к сотруднику
        user.employee.telegram_id = telegram_id
        user.employee.save()

        # Генерируем токены
        refresh = RefreshToken.for_user(user)

        return Response({
            "success": True,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            }
        }, status=200)