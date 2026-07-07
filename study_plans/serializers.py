from rest_framework import serializers
from curriculum.models import SLO
from .models import StudyPlan, StudyPlanSLO

class SLODetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = SLO
        fields = ['id', 'name', 'estimated_time']

class StudyPlanSLOSerializer(serializers.ModelSerializer):
    slo_name = serializers.CharField(source='slo.name', read_only=True)
    slo_no = serializers.CharField(source='slo.slo_no', read_only=True)
    google_drive_link = serializers.CharField(source='slo.google_drive_link', read_only=True)
    difficulty = serializers.CharField(source='slo.difficulty_frequency', read_only=True)

    class Meta:
        model = StudyPlanSLO
        fields = ['id', 'slo', 'slo_no', 'slo_name', 'scheduled_date', 'order_in_day', 'subject_name', 'chapter_name', 'estimated_time', 'is_completed', 'google_drive_link', 'difficulty']

class CreateStudyPlanSerializer(serializers.ModelSerializer):
    slo_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True
    )
    study_time_daily = serializers.IntegerField(default=120)
    min_study_time_daily = serializers.IntegerField(required=False, write_only=True)
    max_study_time_daily = serializers.IntegerField(required=False, write_only=True)

    class Meta:
        model = StudyPlan
        fields = [
            'id', 'title', 'plan_type', 'grade', 'mode', 'start_date', 'end_date', 
            'study_time_daily', 'min_study_time_daily', 'max_study_time_daily', 'custom_pattern', 
            'subject_order', 'slo_ids', 'skip_weekends'
        ]

    def validate(self, data):
        min_study = data.pop('min_study_time_daily', None)
        max_study = data.pop('max_study_time_daily', None)
        if min_study is not None or max_study is not None:
            data['study_time_daily'] = max_study if max_study is not None else min_study

        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("Start date must be before end date.")
        
        if data.get('mode') == StudyPlan.Mode.SEQUENTIAL and not data.get('subject_order'):
            raise serializers.ValidationError("subject_order is required for SEQUENTIAL mode.")
            
        if data.get('mode') == StudyPlan.Mode.CUSTOM and not data.get('custom_pattern'):
            raise serializers.ValidationError("custom_pattern is required for CUSTOM mode.")
            
        # Verify SLOs exist
        slo_ids = data.get('slo_ids', [])
        existing_count = SLO.objects.filter(id__in=slo_ids).count()
        if existing_count != len(set(slo_ids)):
            raise serializers.ValidationError("One or more provided SLO IDs do not exist.")
            
        return data

    def create(self, validated_data):
        model_data = validated_data.copy()
        model_data.pop('slo_ids', None)
        return StudyPlan.objects.create(**model_data)

class StudyPlanSerializer(serializers.ModelSerializer):
    subjects = serializers.SerializerMethodField()

    class Meta:
        model = StudyPlan
        fields = '__all__'

    def get_subjects(self, obj):
        return list(
            obj.scheduled_slos
            .order_by('subject_name')
            .values_list('subject_name', flat=True)
            .distinct()
        )

class StudyPlanDetailSerializer(serializers.ModelSerializer):
    scheduled_slos = StudyPlanSLOSerializer(many=True, read_only=True)
    subjects = serializers.SerializerMethodField()
    
    class Meta:
        model = StudyPlan
        fields = [
            'id', 'title', 'plan_type', 'grade', 'mode', 'start_date', 'end_date',
            'study_time_daily', 'is_completable',
            'total_slo_time', 'total_available_time', 'skip_weekends',
            'current_streak', 'subjects',
            'status', 'created_at', 'scheduled_slos'
        ]

    def get_subjects(self, obj):
        return list(
            obj.scheduled_slos
            .order_by('subject_name')
            .values_list('subject_name', flat=True)
            .distinct()
        )

class ValidatePlanSerializer(serializers.Serializer):
    slo_ids = serializers.ListField(child=serializers.IntegerField())
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    study_time_daily = serializers.IntegerField(default=120)
    skip_weekends = serializers.BooleanField(default=False)


class StudyPlanHistorySerializer(serializers.ModelSerializer):
    scheduled_slos = StudyPlanSLOSerializer(many=True, read_only=True)

    class Meta:
        model = StudyPlan
        fields = [
            'id',
            'title',
            'status',
            'start_date',
            'end_date',
            'plan_type',
            'created_at',
            'scheduled_slos',   
        ]
