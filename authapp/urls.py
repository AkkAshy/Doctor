"""
authapp/urls.py - Authentication & User Management URLs
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenObtainPairView

# Views
from .views import (
    RegisterView,
    ProfileUpdateView,
    GetProfileView,
    ConfirmTelegramCodeView,
    GenerateTelegramCodeView,
    TelegramProfileView,
    HealthRecommendationView
)

# JWT Custom Schemas
from .jwt_schema import LOGIN_SCHEMA, REFRESH_SCHEMA


# ========================================
# APPLY CUSTOM SCHEMAS TO JWT VIEWS
# ========================================

# Create custom classes with schemas
@LOGIN_SCHEMA
class CustomTokenObtainPairView(TokenObtainPairView):
    pass

@REFRESH_SCHEMA
class CustomTokenRefreshView(TokenRefreshView):
    pass


# ========================================
# URL PATTERNS
# ========================================

urlpatterns = [
    # ========================================
    # JWT AUTHENTICATION
    # ========================================
    
    # Login (получить JWT токены)
    path(
        'login/',
        CustomTokenObtainPairView.as_view(),
        name='login'
    ),
    
    # Refresh Token (обновить access token)
    path(
        'token/refresh/',
        CustomTokenRefreshView.as_view(),
        name='token_refresh'
    ),
    
    # ========================================
    # USER MANAGEMENT
    # ========================================
    
    # Registration (регистрация нового пользователя)
    path(
        'register/',
        RegisterView.as_view(),
        name='register'
    ),
    
    # Update Profile (обновление профиля)
    path(
        'profile/',
        ProfileUpdateView.as_view(),
        name='profile-update'
    ),
    
    # Get My Profile (получить свой профиль)
    path(
        'my-profile/',
        GetProfileView.as_view(),
        name='profile-view'
    ),
    
    # ========================================
    # TELEGRAM INTEGRATION
    # ========================================
    
    # Generate Telegram Auth Code (сгенерировать код для привязки)
    path(
        'telegram/generate_code/',
        GenerateTelegramCodeView.as_view(),
        name='telegram_generate_code'
    ),
    
    # Confirm Telegram Code (подтвердить код и привязать аккаунт)
    path(
        'telegram/confirm_code/',
        ConfirmTelegramCodeView.as_view(),
        name='telegram_confirm_code'
    ),
    
    # Get Profile by Telegram ID (получить профиль по Telegram ID)
    path(
        'telegram/profile/<int:telegram_id>/',
        TelegramProfileView.as_view(),
        name='telegram_profile'
    ),
    
    # ========================================
    # AI RECOMMENDATIONS
    # ========================================
    
    # Get AI Recommendations (получить персональные рекомендации)
    path(
        'recomended/',
        HealthRecommendationView.as_view(),
        name='recommendations'
    ),
]