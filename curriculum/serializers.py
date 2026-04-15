from rest_framework import serializers
from .models import Subject, Chapter, SLO

class SubjectSerializer(serializers.ModelSerializer):
    chapter_count = serializers.IntegerField(read_only=True)
    topic_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Subject
        fields = ['id', 'name', 'description', 'grade', 'created_at', 'chapter_count', 'topic_count']

class SLOSerializer(serializers.ModelSerializer):
    class Meta:
        model = SLO
        fields = ['id', 'chapter', 'name', 'difficulty_frequency', 'estimated_time', 'created_at']

class ChapterSerializer(serializers.ModelSerializer):
    slos = SLOSerializer(many=True, read_only=True)
    topic_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Chapter
        fields = ['id', 'subject', 'name', 'created_at', 'slos', 'topic_count']
