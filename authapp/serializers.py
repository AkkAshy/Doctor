# auth/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Employee, HealthRecommendation

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ['role', 'phone', 'photo']
        extra_kwargs = {
            'photo': {'required': False, 'allow_null': True}
        }


class HealthRecommendationSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.user.get_full_name", read_only=True)

    class Meta:
        model = HealthRecommendation
        fields = ["id", "employee", "employee_name", "text", "created_at"]
        read_only_fields = ["id", "employee", "employee_name", "created_at"]

class UserSerializer(serializers.ModelSerializer):
    employee = EmployeeSerializer()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password', 'employee']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        employee_data = validated_data.pop('employee')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        Employee.objects.create(user=user, **employee_data)
        return user


    def update(self, instance, validated_data):
        employee_data = validated_data.pop('employee')
        employee = instance.employee

        # Обновляем поля пользователя
        instance.username = validated_data.get('username', instance.username)
        instance.email = validated_data.get('email', instance.email)
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.save()


        # Обновляем данные сотрудника
        employee.role = employee_data.get('role', employee.role)
        employee.phone = employee_data.get('phone', employee.phone)
        employee.photo = employee_data.get('photo', employee.photo)
        employee.save()

        return instance

