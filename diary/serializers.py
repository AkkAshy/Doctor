from rest_framework import serializers
from .models import GlucoseMeasurement, Event, Medication, StressNote, Reminder, MealPhoto

class GlucoseMeasurementSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlucoseMeasurement
        fields = ["id", "employee", "value", "measured_at"]
        read_only_fields = ["id", "employee", "measured_at"]


class MealPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealPhoto
        fields = ["id", "employee", "meal", "image", "uploaded_at", "food_name", "sugars"]
        read_only_fields = ["id", "employee", "uploaded_at"]

    def validate_meal(self, value):
        if value.type != "meal":
            raise serializers.ValidationError("Фото можно привязывать только к событию типа 'meal'")
        return value


class EventSerializer(serializers.ModelSerializer):
    photos = MealPhotoSerializer(many=True, read_only=True)
    slug = serializers.ReadOnlyField()

    # Добавляем поля для загрузки фото
    image = serializers.ImageField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Event
        fields = [
            "id", "employee", "type", "name", "description",
            "calories", "carbs", "sugars",
            "duration", "steps",
            "start_time", "end_time",
            "photos", "slug", "color",
            "image"  # ← НОВОЕ ПОЛЕ
        ]
        read_only_fields = ["id", "employee", "slug"]

    def validate(self, data):
        """
        Если тип события = meal и есть фото, автоматически анализируем
        """
        event_type = data.get('type')
        image = data.get('image')

        # Если это еда и есть фото - анализируем
        if event_type == 'meal' and image:
            from .utils import analyze_food_image

            analysis = analyze_food_image(image)

            if analysis.get('success'):
                # Автоматически заполняем поля из анализа (если они не указаны)
                if not data.get('name'):
                    data['name'] = analysis['food_name'][:15]

                if not data.get('calories'):
                    data['calories'] = analysis['calories']

                if not data.get('carbs'):
                    data['carbs'] = analysis['carbs']

                if not data.get('sugars'):
                    data['sugars'] = analysis['sugars']

                if not data.get('description'):
                    data['description'] = analysis.get('description', '')

                # Сохраняем результат анализа для использования в create()
                data['_analysis_result'] = analysis
            else:
                # Если анализ не удался, но фото есть - всё равно сохраняем
                data['_analysis_result'] = None

        return data

    def create(self, validated_data):
        # Извлекаем фото и результат анализа
        image = validated_data.pop('image', None)
        analysis_result = validated_data.pop('_analysis_result', None)

        # Создаем событие
        event = super().create(validated_data)

        # Если было фото - сохраняем его
        if image and event.type == 'meal':
            MealPhoto.objects.create(
                employee=event.employee,
                meal=event,
                image=image,
                food_name=analysis_result.get('food_name') if analysis_result else None,
                sugars=analysis_result.get('sugars') if analysis_result else None
            )

        return event


class MedicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medication
        fields = ["id", "employee", "name", "dose", "taken_at"]
        read_only_fields = ["id", "employee"]


class StressNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = StressNote
        fields = ["id", "employee", "description", "noted_at"]
        read_only_fields = ["id", "employee", "noted_at"]


class ReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reminder
        fields = ["id", "employee", "text", "remind_at", "is_done", "created_at"]
        read_only_fields = ["id", "employee", "created_at"]


class FoodAnalysisSerializer(serializers.Serializer):
    """
    Сериализатор для анализа фото еды без сохранения в БД
    """
    image = serializers.ImageField(required=True)

    def validate_image(self, value):
        # Проверка размера файла (макс 10MB)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("Размер изображения не должен превышать 10MB")

        # Проверка типа файла
        allowed_types = ['image/jpeg', 'image/png', 'image/jpg', 'image/webp']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                f"Неподдерживаемый формат. Разрешены: {', '.join(allowed_types)}"
            )

        return value