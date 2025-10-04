# your_app/celery_tasks.py
from celery import shared_task
from .models import Employee
from .tasks import generate_recommendation_for_employee

@shared_task
def generate_recommendations_for_all():
    for emp in Employee.objects.all():
        generate_recommendation_for_employee(emp)
