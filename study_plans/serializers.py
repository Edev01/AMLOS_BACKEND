from rest_framework import serializers
from curriculum.models import SLO
from .models import StudyPlan, StudyPlanSLO

class SLODetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = SLO
        fields = ['id', 'name', 'estimated_time']

class StudyPlanSLOSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyPlanSLO
        fields = ['id', 'slo', 'scheduled_date', 'order_in_day', 'subject_name', 'chapter_name', 'estimated_time', 'is_completed']

class CreateStudyPlanSerializer(serializers.ModelSerializer):
    slo_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True
    )

    class Meta:
        model = StudyPlan
        fields = [
            'id', 'title', 'plan_type', 'grade', 'mode', 'start_date', 'end_date', 
            'min_study_time_daily', 'max_study_time_daily', 'custom_pattern', 
            'subject_order', 'slo_ids'
        ]

    def validate(self, data):
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
    class Meta:
        model = StudyPlan
        fields = '__all__'

class StudyPlanDetailSerializer(serializers.ModelSerializer):
    scheduled_slos = StudyPlanSLOSerializer(many=True, read_only=True)
    
    class Meta:
        model = StudyPlan
        fields = [
            'id', 'title', 'plan_type', 'grade', 'mode', 'start_date', 'end_date',
            'min_study_time_daily', 'max_study_time_daily', 'is_completable',
            'total_slo_time', 'total_available_time', 
            'status', 'created_at', 'scheduled_slos'
        ]

class ValidatePlanSerializer(serializers.Serializer):
    slo_ids = serializers.ListField(child=serializers.IntegerField())
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    min_study_time_daily = serializers.IntegerField(default=120)
    max_study_time_daily = serializers.IntegerField(default=300)
