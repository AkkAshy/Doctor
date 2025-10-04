# diary/models.py
from django.db import models
from authapp.models import Employee
from datetime import timedelta


class GlucoseMeasurement(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="glucose_measurements")
    value = models.FloatField(help_text="Уровень сахара (ммоль/л)")
    measured_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-measured_at"]

    def __str__(self):
        return f"{self.employee.user.get_full_name()} – {self.value} ммоль/л ({self.measured_at})"

class Event(models.Model):
    EVENT_TYPES = [
        ("meal", "Прием пищи"),
        ("walk", "Прогулка"),
        ("sport", "Спорт"),
        ("other", "Другое"),
        ("medicine", "Лекарство"),
    ]

    color = models.CharField(max_length=20, blank=True, null=True)

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="events")
    type = models.CharField(max_length=20, choices=EVENT_TYPES, default="other")
    name = models.CharField(max_length=15, blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)

    # Для еды
    calories = models.FloatField(null=True, blank=True, help_text="Ккал")
    carbs = models.FloatField(null=True, blank=True, help_text="Углеводы (г)")
    sugars = models.FloatField(null=True, blank=True, help_text="Сахара (г)")

    # Для активности
    duration = models.IntegerField(null=True, blank=True, help_text="Минуты")
    steps = models.IntegerField(null=True, blank=True)

    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)  # можно вычислять через start_time + duration

    class Meta:
        ordering = ["-start_time"]

    @property
    def slug(self):
        # слаг для фронта, по типу события
        return self.type.lower()

    def save(self, *args, **kwargs):
        # Если end_time не задан, и есть duration — вычисляем
        if not self.end_time and self.duration:
            self.end_time = self.start_time + timedelta(minutes=self.duration)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.user.get_full_name()} – {self.type} ({self.start_time})"



class Medication(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="medications")
    name = models.CharField(max_length=255)
    dose = models.CharField(max_length=50)
    taken_at = models.DateTimeField()

    class Meta:
        ordering = ["-taken_at"]

    def __str__(self):
        return f"{self.employee.user.get_full_name()} – {self.name} ({self.dose}) ({self.taken_at})"


class StressNote(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="stress_notes")
    description = models.TextField()
    noted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-noted_at"]

    def __str__(self):
        return f"{self.employee.user.get_full_name()} – {self.description} ({self.noted_at})"


class Reminder(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="reminders")
    text = models.CharField(max_length=255)
    remind_at = models.DateTimeField()
    is_done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-remind_at"]

    def __str__(self):
        return f"{self.employee.user.get_full_name()} – {self.text} ({self.remind_at})"


class MealPhoto(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="meal_photos")
    meal = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="photos",
        null=True,
        blank=True
    )
    image = models.ImageField(upload_to="meals/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    food_name = models.CharField(max_length=255, blank=True, null=True)
    sugars = models.FloatField(blank=True, null=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.employee.user.get_full_name()} – {self.food_name or 'Фото еды'} ({self.uploaded_at})"

    def save(self, *args, **kwargs):
        # проверяем, что meal действительно type="meal"
        if self.meal and self.meal.type != "meal":
            raise ValueError("Фото можно привязывать только к событию типа 'meal'")
        super().save(*args, **kwargs)
