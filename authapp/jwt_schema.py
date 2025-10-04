# authapp/jwt_schema.py
from drf_spectacular.utils import extend_schema, OpenApiExample
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class JWTAuthenticationScheme(OpenApiAuthenticationExtension):
    """
    Кастомная схема аутентификации для JWT в Swagger
    """
    target_class = 'rest_framework_simplejwt.authentication.JWTAuthentication'
    name = 'JWTAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
            'description': 'Введите JWT токен в формате: Bearer <token>'
        }


# Схемы для login endpoint
LOGIN_SCHEMA = extend_schema(
    tags=['Авторизация'],
    summary="Вход в систему",
    description="""
    Аутентификация пользователя и получение JWT токенов.
    
    **Процесс:**
    1. Отправьте username и password
    2. Получите access и refresh токены
    3. Используйте access token для авторизации API запросов
    4. Когда access истечет, обновите через refresh token
    
    **Срок действия токенов:**
    - Access token: 9 дней
    - Refresh token: 15 дней
    """,
    request={
        "type": "object",
        "properties": {
            "username": {"type": "string", "example": "ivan_petrov"},
            "password": {"type": "string", "example": "SecurePass123"}
        },
        "required": ["username", "password"]
    },
    responses={
        200: {
            "type": "object",
            "properties": {
                "refresh": {
                    "type": "string",
                    "description": "Refresh token для обновления access token"
                },
                "access": {
                    "type": "string",
                    "description": "Access token для авторизации запросов"
                }
            }
        },
        401: {
            "description": "Неверные учетные данные"
        }
    },
    examples=[
        OpenApiExample(
            "Пример запроса",
            value={
                "username": "ivan_petrov",
                "password": "SecurePass123"
            },
            request_only=True
        ),
        OpenApiExample(
            "Успешный ответ",
            value={
                "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            },
            response_only=True,
            status_codes=['200']
        )
    ]
)


# Схема для refresh endpoint
REFRESH_SCHEMA = extend_schema(
    tags=['Авторизация'],
    summary="Обновить access token",
    description="""
    Получение нового access token с помощью refresh token.
    
    **Когда использовать:**
    - Когда access token истек (обычно через 9 дней)
    - Перед выполнением важных операций для гарантии валидности токена
    
    **Примечание:** После обновления вы получите новую пару токенов (если включена ротация).
    """,
    request={
        "type": "object",
        "properties": {
            "refresh": {
                "type": "string",
                "description": "Refresh token, полученный при входе"
            }
        },
        "required": ["refresh"]
    },
    responses={
        200: {
            "type": "object",
            "properties": {
                "access": {"type": "string", "description": "Новый access token"},
                "refresh": {"type": "string", "description": "Новый refresh token (если ротация включена)"}
            }
        },
        401: {
            "description": "Refresh token недействителен или истек"
        }
    },
    examples=[
        OpenApiExample(
            "Пример запроса",
            value={
                "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            },
            request_only=True
        ),
        OpenApiExample(
            "Успешный ответ",
            value={
                "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            },
            response_only=True,
            status_codes=['200']
        )
    ]
)