from rest_framework import serializers
from .models import Subject, Chapter, SLO

class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'name', 'description', 'board_exam_date', 'created_at']

class ChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chapter
        fields = ['id', 'subject', 'name', 'created_at']

class SLOSerializer(serializers.ModelSerializer):
    class Meta:
        model = SLO
        fields = ['id', 'chapter', 'name', 'difficulty_frequency', 'estimated_time', 'created_at']
