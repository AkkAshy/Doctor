from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    GlucoseMeasurementViewSet, EventViewSet,
    MedicationViewSet, StressNoteViewSet,
    ReminderViewSet, MealPhotoViewSet
)
from .statistics_views import ActivityStatisticsView, GlucoseStatisticsView, NutritionStatisticsView



router = DefaultRouter()
router.register(r'glucose', GlucoseMeasurementViewSet, basename='glucose')
router.register(r'events', EventViewSet, basename='events')
router.register(r'meal-photos', MealPhotoViewSet, basename='meal-photos')
router.register(r'medications', MedicationViewSet, basename='medications')
router.register(r'stress-notes', StressNoteViewSet, basename='stress-notes')
router.register(r'reminders', ReminderViewSet, basename='reminders')

urlpatterns = [
    path('', include(router.urls)),
    path('statistics/glucose/', GlucoseStatisticsView.as_view(), name='glucose-statistics'),
    path('statistics/nutrition/', NutritionStatisticsView.as_view(), name='nutrition-statistics'),
    path('statistics/activity/', ActivityStatisticsView.as_view(), name='activity-statistics'),
]
