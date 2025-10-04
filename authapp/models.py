# auth/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
import uuid
from datetime import timedelta

from django.utils import timezone
import random
import string




class Employee(models.Model):
    ROLE_CHOICES = (
        ('admin', _('Админ')),
        ('doctor', _('Врач')),
        ('user', _('Пользователь')),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    phone = models.CharField(max_length=20, blank=True, null=True)
    photo = models.ImageField(upload_to='employee_photos/', blank=True, null=True)
    telegram_id = models.CharField(max_length=50, blank=True, null=True)
    telegram_username = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Сотрудник')
        verbose_name_plural = _('Сотрудники')

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.role})"

    def is_doctor(self):
        return self.role == 'doctor'

    def is_admin(self):
        return self.role == 'admin'

    def is_user(self):
        return self.role == 'user'

class HealthRecommendation(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="recommendations")
    text = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Рекомендация для {self.employee.user.username} от {self.created_at:%d.%m.%Y}"


class TelegramAuthCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    created_at = models.DateTimeField(default=timezone.now)
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("Telegram-код авторизации")
        verbose_name_plural = _("Telegram-коды авторизации")

    def __str__(self):
        return f"{self.user.username} — {self.code} ({'использован' if self.is_used else 'активен'})"

    def is_valid(self):
        """Код действителен 5 минут и не должен быть использован ранее."""
        return (
            not self.is_used
            and (timezone.now() - self.created_at).total_seconds() < 900
        )

    @classmethod
    def generate_for_user(cls, user):
        cls.objects.filter(user=user, is_used=False).update(is_used=True)
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        new_code = cls.objects.create(user=user, code=code)
        return new_code.code

    @classmethod
    def verify_code(cls, code):
        # Проверяем, существует ли и не старше 10 минут
        try:
            record = cls.objects.get(code=code)
        except cls.DoesNotExist:
            return None

        if timezone.now() - record.created_at > timedelta(minutes=30):
            record.delete()
            return None

        user = record.user
        record.delete()
        return user