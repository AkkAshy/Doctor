# auth/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, viewsets
from rest_framework.decorators import action
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from .models import Employee, TelegramAuthCode, HealthRecommendation
from .serializers import UserSerializer, HealthRecommendationSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from .tasks import get_comprehensive_analysis
import logging


logger = logging.getLogger(__name__)


class HealthRecommendationView(APIView):
    """
    Генерирует рекомендации на лету без сохранения
    GET /api/users/recomended/
    """
    permission_classes = [permissions.IsAuthenticated]

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
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """
        Регистрация нового пользователя.

        Параметры:
        - username (str)
        - email (str)
        - password (str)
        - first_name (str)
        - last_name (str)
        - employee (dict):
            - role (str)
            - phone (str)
            - photo (file)

        Возвращает:
        - access/refresh JWT токены
        - данные пользователя
        """
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
    permission_classes = [permissions.AllowAny]

    def get(self, request, telegram_id):
        """
        Получить профиль пользователя по Telegram ID
        GET /api/users/telegram/profile/<telegram_id>/
        """
        try:
            employee = Employee.objects.select_related("user").get(telegram_id=telegram_id)
            serializer = UserSerializer(employee.user)
            return Response(serializer.data)
        except Employee.DoesNotExist:
            return Response({"error": "Профиль не найден"}, status=404)


class GetProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        Получение данных о пользователе.

        GET /api/users/profile/
        """
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data)


class ProfileUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request):
        """
        Обновление профиля пользователя

        PUT /api/users/profile/

        Request Body:
            {
                "username": "string",
                "email": "string",
                "first_name": "string",
                "last_name": "string",
                "employee": {
                    "role": "string",
                    "phone": "string",
                    "photo": "string"
                }
            }

        Response:
            200: {
                "id": integer,
                "username": "string",
                "email": "string",
                "first_name": "string",
                "last_name": "string",
                "employee": {
                    "role": "string",
                    "phone": "string",
                    "photo": "string"
                }
            }
            400: {
                "error": "string"
            }
        """
        user = request.user
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GenerateTelegramCodeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        Генерация кода для привязки Telegram

        GET /api/users/telegram/generate-code/
        """
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
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """
        Подтверждение кода и привязка Telegram ID

        POST /api/users/telegram/confirm-code/

        Request Body:
        {
            "code": "string",
            "telegram_id": "string"
        }
        """
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