"""
healthapp/urls.py - Main URL Configuration
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Swagger/OpenAPI Documentation
from drf_spectacular.views import (
    SpectacularAPIView,           # JSON Schema
    SpectacularSwaggerView,        # Swagger UI
    SpectacularRedocView          # ReDoc UI
)

# Statistics Views (альтернативные пути)
from diary.statistics_views import (
    ActivityStatisticsView,
    GlucoseStatisticsView,
    NutritionStatisticsView
)


# ========================================
# MAIN URL PATTERNS
# ========================================

urlpatterns = [
    # ========================================
    # DJANGO ADMIN PANEL
    # ========================================
    path('admin/', admin.site.urls),
    
    
    # ========================================
    # API ENDPOINTS
    # ========================================
    
    # Authentication & User Management
    # /api/users/login/, /api/users/register/, etc.
    path('api/users/', include('authapp.urls')),
    
    # Diary (Glucose, Events, Medications, Stress, Reminders)
    # /api/diary/glucose/, /api/diary/events/, etc.
    path('api/diary/', include('diary.urls')),
    
    # Doctor API (только для врачей)
    # /api/doctor/patients/, /api/doctor/dashboard/, etc.
    path('api/doctor/', include('diary.doctor_urls')),
    
    
    # ========================================
    # ALTERNATIVE STATISTICS PATHS
    # (Дублируют пути из diary/urls.py для удобства)
    # ========================================
    
    # Activity Statistics
    # GET /api/statistics/activity/?period=month&type=meal
    path(
        'api/statistics/activity/',
        ActivityStatisticsView.as_view(),
        name='user-statistics-activity'
    ),
    
    # Glucose Statistics
    # GET /api/statistics/glucose/?period=month
    path(
        'api/statistics/glucose/',
        GlucoseStatisticsView.as_view(),
        name='user-statistics-glucose'
    ),
    
    # Nutrition Statistics
    # GET /api/statistics/nutrition/?period=3months
    path(
        'api/statistics/nutrition/',
        NutritionStatisticsView.as_view(),
        name='user-statistics-nutrition'
    ),
    
    
    # ========================================
    # SWAGGER / OPENAPI DOCUMENTATION
    # ========================================
    
    # OpenAPI 3.0 Schema (JSON)
    # Скачать схему для импорта в Postman, генерации клиентов и т.д.
    path(
        'api/schema/',
        SpectacularAPIView.as_view(),
        name='schema'
    ),
    
    # Swagger UI - Интерактивная документация
    # Основной интерфейс для тестирования API
    # http://127.0.0.1:8000/api/docs/
    path(
        'api/docs/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui'
    ),
    
    # ReDoc - Альтернативная документация
    # Красивая документация с поиском и навигацией
    # http://127.0.0.1:8000/api/redoc/
    path(
        'api/redoc/',
        SpectacularRedocView.as_view(url_name='schema'),
        name='redoc'
    ),
]


# ========================================
# SERVE STATIC & MEDIA FILES (Development)
# ========================================

if settings.DEBUG:
    # Media files (uploaded images, etc.)
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
    
    # Static files (CSS, JS, etc.)
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT
    )


# ========================================
# CUSTOM ERROR HANDLERS (Optional)
# ========================================

# Uncomment to use custom error pages
# handler404 = 'healthapp.views.custom_404'
# handler500 = 'healthapp.views.custom_500'
# handler403 = 'healthapp.views.custom_403'
# handler400 = 'healthapp.views.custom_400'


# ========================================
# URL SUMMARY
# ========================================

"""
Available URLs:

ADMIN:
  /admin/                                    - Django Admin Panel

AUTHENTICATION:
  /api/users/login/                          - JWT Login
  /api/users/token/refresh/                  - Refresh Token
  /api/users/register/                       - Register New User
  /api/users/profile/                        - Update Profile
  /api/users/my-profile/                     - Get My Profile
  /api/users/telegram/generate_code/         - Generate Telegram Code
  /api/users/telegram/confirm_code/          - Confirm Telegram Code
  /api/users/telegram/profile/<telegram_id>/ - Get Profile by Telegram ID
  /api/users/recomended/                     - AI Recommendations

DIARY:
  /api/diary/glucose/                        - Glucose CRUD
  /api/diary/events/                         - Events CRUD
  /api/diary/events/preview_meal/            - AI Analyze Food Photo
  /api/diary/events/create_meal_with_photo/  - Create Meal with AI
  /api/diary/meal-photos/                    - Meal Photos CRUD
  /api/diary/medications/                    - Medications CRUD
  /api/diary/stress-notes/                   - Stress Notes CRUD
  /api/diary/reminders/                      - Reminders CRUD
  /api/diary/statistics/glucose/             - Glucose Statistics
  /api/diary/statistics/nutrition/           - Nutrition Statistics
  /api/diary/statistics/activity/            - Activity Statistics

DOCTOR (role='doctor' required):
  /api/doctor/patients/                      - List Patients
  /api/doctor/patients/<id>/                 - Patient Details
  /api/doctor/patients/<id>/statistics/      - Patient Statistics
  /api/doctor/glucose/                       - All Glucose Data
  /api/doctor/events/                        - All Events Data
  /api/doctor/medications/                   - All Medications Data
  /api/doctor/stress-notes/                  - All Stress Notes Data
  /api/doctor/dashboard/                     - Doctor Dashboard

STATISTICS (alternative paths):
  /api/statistics/activity/                  - Activity Statistics
  /api/statistics/glucose/                   - Glucose Statistics
  /api/statistics/nutrition/                 - Nutrition Statistics

DOCUMENTATION:
  /api/docs/                                 - Swagger UI (Interactive)
  /api/redoc/                                - ReDoc (Beautiful)
  /api/schema/                               - OpenAPI Schema (JSON)
"""