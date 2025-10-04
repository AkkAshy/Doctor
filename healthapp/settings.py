from pathlib import Path
from datetime import timedelta
import os
from django.core.exceptions import ImproperlyConfigured
from decouple import config

# OpenAI API Key
OPENAI_API_KEY = config("OPENAI_API_KEY")

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-9@d!c$v)0_uad#$%7h+hjan^8fu4c(-j(!4hwz75pfhfx%+v9f'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    "mahallaxoj.pythonanywhere.com",
    "127.0.0.1",
    "localhost",
]

# Telegram Bot
TELEGRAM_BOT_USERNAME = 'Gluzone_Bot'

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'drf_spectacular',  # Swagger/OpenAPI

    # Local apps
    'authapp',
    'diary',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

CORS_ALLOW_CREDENTIALS = True

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
    'DATE_FORMAT': '%Y-%m-%d',
    
    # Swagger Schema
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# drf-spectacular settings for Swagger/OpenAPI
SPECTACULAR_SETTINGS = {
    'TITLE': 'GluZone API - Система мониторинга здоровья',
    'DESCRIPTION': """
# GluZone Health Monitoring System API

Полная документация REST API для системы мониторинга здоровья пациентов с диабетом.

## 🌟 Основные возможности:

### 🔐 Авторизация
- JWT токены (access + refresh)
- Telegram OAuth интеграция
- Автоматическое обновление токенов

### 📊 Дневник здоровья
- **Глюкоза**: замеры уровня сахара в крови
- **События**: приёмы пищи, прогулки, спорт
- **Лекарства**: учёт принятых медикаментов
- **Стресс**: заметки о самочувствии
- **Напоминания**: система уведомлений

### 🤖 AI-функции
- **Анализ фото еды** через GPT-4 Vision
- **Персональные рекомендации** от AI
- **Прогноз глюкозы** на 7 дней вперёд

### 📈 Статистика и аналитика
- Графики уровня глюкозы
- Статистика питания (калории, углеводы, сахара)
- Анализ физической активности
- Тренды и паттерны

### 👨‍⚕️ Для врачей
- Просмотр данных всех пациентов
- Детальная статистика по каждому пациенту
- Дашборд с критическими случаями
- Фильтрация и поиск

## 🔑 Авторизация

Используйте JWT токены для доступа к API:

1. Получите токен через `/api/users/login/`
2. Добавьте в заголовки запросов:
   ```
   Authorization: Bearer <ваш_access_token>
   ```

## 👥 Роли пользователей

- **user** - обычный пользователь (видит только свои данные)
- **doctor** - врач (видит данные всех пациентов)
- **admin** - администратор

## 📱 Telegram Bot

Для связи аккаунта с Telegram используйте эндпоинты `/api/users/telegram/*`

## 🚀 Быстрый старт

1. Зарегистрируйтесь: `POST /api/users/register/`
2. Войдите: `POST /api/users/login/`
3. Нажмите "Authorize" вверху и введите токен
4. Тестируйте API!
    """,
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    
    # UI Settings
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
        'filter': True,
        'defaultModelsExpandDepth': 2,
        'defaultModelExpandDepth': 2,
    },
    
    'COMPONENT_SPLIT_REQUEST': True,
    'SORT_OPERATIONS': False,
    
    # Tags для группировки endpoints
    'TAGS': [
        {
            'name': 'Авторизация',
            'description': 'Регистрация, вход в систему, управление профилем пользователя'
        },
        {
            'name': 'Telegram',
            'description': 'Интеграция с Telegram ботом для удобного доступа'
        },
        {
            'name': 'Дневник - Глюкоза',
            'description': 'Измерения уровня глюкозы в крови'
        },
        {
            'name': 'Дневник - События',
            'description': 'События: приёмы пищи, прогулки, спортивные активности'
        },
        {
            'name': 'Дневник - Лекарства',
            'description': 'Учёт принятых лекарств и медикаментов'
        },
        {
            'name': 'Дневник - Стресс',
            'description': 'Заметки о стрессе и общем самочувствии'
        },
        {
            'name': 'Дневник - Напоминания',
            'description': 'Напоминания о приёме лекарств, измерениях и т.д.'
        },
        {
            'name': 'Дневник - Фото еды',
            'description': 'Загрузка и AI-анализ фотографий еды с помощью GPT-4 Vision'
        },
        {
            'name': 'Статистика',
            'description': 'Графики, аналитика и статистические данные'
        },
        {
            'name': 'AI Рекомендации',
            'description': 'Персонализированные рекомендации и прогнозы от GPT-4'
        },
        {
            'name': 'Врач - Пациенты',
            'description': 'Управление списком пациентов (только для врачей)'
        },
        {
            'name': 'Врач - Данные',
            'description': 'Просмотр данных пациентов (только для врачей)'
        },
        {
            'name': 'Врач - Дашборд',
            'description': 'Общая статистика и критические случаи (только для врачей)'
        },
    ],
    
    # Servers
    'SERVERS': [
        {
            'url': 'http://127.0.0.1:8000',
            'description': 'Development Server'
        },
        {
            'url': 'https://mahallaxoj.pythonanywhere.com',
            'description': 'Production Server'
        },
    ],
}

# Simple JWT settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=9),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=15),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

ROOT_URLCONF = 'healthapp.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
            ],
        },
    },
]

WSGI_APPLICATION = 'healthapp.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB

ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/jpg', 'image/webp']

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'debug.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Security settings for production
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True