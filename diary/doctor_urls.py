# diary/doctor_urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .doctor_views import (
    DoctorPatientViewSet,
    DoctorGlucoseViewSet,
    DoctorEventViewSet,
    DoctorMedicationViewSet,
    DoctorStressNoteViewSet,
    DoctorDashboardViewSet
)

router = DefaultRouter()
router.register(r'patients', DoctorPatientViewSet, basename='doctor-patients')
router.register(r'glucose', DoctorGlucoseViewSet, basename='doctor-glucose')
router.register(r'events', DoctorEventViewSet, basename='doctor-events')
router.register(r'medications', DoctorMedicationViewSet, basename='doctor-medications')
router.register(r'stress-notes', DoctorStressNoteViewSet, basename='doctor-stress-notes')
router.register(r'dashboard', DoctorDashboardViewSet, basename='doctor-dashboard')

urlpatterns = [
    path('', include(router.urls)),
]