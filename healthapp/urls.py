from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from diary.statistics_views import (
    ActivityStatisticsView,
    GlucoseStatisticsView,
    NutritionStatisticsView
)


urlpatterns = [ 
    path('admin/', admin.site.urls),
    path('api/users/', include('authapp.urls')),
    path('api/diary/', include('diary.urls')),
    path('api/doctor/', include('diary.doctor_urls')),
    
    # Statistics endpoints для обычных пользователей
    path('api/statistics/activity/', ActivityStatisticsView.as_view(), name='user-statistics-activity'),
    path('api/statistics/glucose/', GlucoseStatisticsView.as_view(), name='user-statistics-glucose'),
    path('api/statistics/nutrition/', NutritionStatisticsView.as_view(), name='user-statistics-nutrition'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)