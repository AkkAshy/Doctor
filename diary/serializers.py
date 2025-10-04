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
    photos = MealPhotoSerializer(many=True, read_only=True)  # фото еды, если type="meal"
    slug = serializers.ReadOnlyField()  # для фронта

    class Meta:
        model = Event
        fields = [
            "id", "employee", "type", "name", "description",
            "calories", "carbs", "sugars",
            "duration", "steps",
            "start_time", "end_time",
            "photos", "slug", "color"
        ]
        read_only_fields = ["id", "employee", "slug"]


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
