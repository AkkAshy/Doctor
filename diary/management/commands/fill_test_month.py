# management/commands/fill_test_month.py
import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from diary.models import Employee, GlucoseMeasurement, Event, Medication, StressNote

class Command(BaseCommand):
    help = "Заполняет тестового пользователя данными за месяц"

    def handle(self, *args, **kwargs):
        employee = Employee.objects.get(user__username="Akkanat")
        now = timezone.now()
        start_date = now - timedelta(days=30)

        # ====== Глюкоза ======
        for i in range(30):
            day = start_date + timedelta(days=i)
            for hour in [7, 12, 19]:  # утро, день, вечер
                value = round(random.uniform(4.5, 9.5), 1)
                GlucoseMeasurement.objects.create(
                    employee=employee,
                    value=value,
                    measured_at=day.replace(hour=hour, minute=0)
                )

        # ====== События ======
        meal_types = ['meal', 'sport', 'walk']
        for i in range(30):
            day = start_date + timedelta(days=i)
            # Завтрак
            Event.objects.create(
                employee=employee,
                type='meal',
                description='Завтрак: овсянка с фруктами',
                calories=350,
                carbs=45,
                sugars=12,
                start_time=day.replace(hour=8, minute=0)
            )
            # Обед
            Event.objects.create(
                employee=employee,
                type='meal',
                description='Обед: рис с курицей',
                calories=600,
                carbs=60,
                sugars=8,
                start_time=day.replace(hour=13, minute=0)
            )
            # Прогулка
            Event.objects.create(
                employee=employee,
                type='walk',
                description='Прогулка 30 минут',
                steps=4000,
                duration=30,
                start_time=day.replace(hour=17, minute=0)
            )
            # Спорт (2 раза в неделю)
            if i % 3 == 0:
                Event.objects.create(
                    employee=employee,
                    type='sport',
                    description='Тренировка: лёгкая разминка',
                    duration=45,
                    start_time=day.replace(hour=19, minute=0)
                )

        # ====== Лекарства ======
        for i in range(30):
            day = start_date + timedelta(days=i)
            if i % 2 == 0:
                Medication.objects.create(
                    employee=employee,
                    name='Инсулин',
                    dose='10 ед.',
                    taken_at=day.replace(hour=7, minute=30)
                )

        # ====== Стресс ======
        for i in range(0, 30, 7):
            day = start_date + timedelta(days=i)
            StressNote.objects.create(
                employee=employee,
                description='Немного стрессовал на работе',
                noted_at=day.replace(hour=20, minute=0)
            )

        self.stdout.write(self.style.SUCCESS('✅ Данные за месяц успешно сгенерированы!'))
