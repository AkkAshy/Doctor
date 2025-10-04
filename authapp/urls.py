# auth/urls.py
from django.urls import path
from django.urls import path, include
from .views import  RegisterView, ProfileUpdateView, GetProfileView, ConfirmTelegramCodeView
from rest_framework_simplejwt.views import TokenRefreshView, TokenObtainPairView
from .views import GenerateTelegramCodeView, TelegramProfileView, HealthRecommendationViewSet
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register(r'recomended', HealthRecommendationViewSet, basename='recomended')

urlpatterns = [
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', ProfileUpdateView.as_view(), name='profile-update'),
    path('my-profile/', GetProfileView.as_view(), name='profile-view'),

    # 🔗 Telegram Auth
    path('telegram/generate_code/', GenerateTelegramCodeView.as_view(), name='telegram_generate_code'),
    path('telegram/confirm_code/', ConfirmTelegramCodeView.as_view()),
    path("telegram/profile/<int:telegram_id>/", TelegramProfileView.as_view()),
    path('', include(router.urls)),

]
