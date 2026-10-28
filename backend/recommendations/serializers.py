from rest_framework import serializers
from .models import CareerRecommendation, TopRole, JobRole


class TopRoleSerializer(serializers.ModelSerializer):
    """Serializer untuk Top Role recommendations."""
    
    class Meta:
        model = TopRole
        fields = [
            'id', 'role_title', 'category', 'match_percentage',
            'rank', 'salary_range'
        ]
        read_only_fields = ['id', 'rank']


class CareerRecommendationSerializer(serializers.ModelSerializer):
    """Serializer untuk Career Recommendation dengan nested TopRoles."""
    
    top_roles = TopRoleSerializer(many=True, read_only=True)
    
    class Meta:
        model = CareerRecommendation
        fields = [
            'id', 'resume', 'dominant_category', 'profile_summary',
            'detected_skills', 'learning_path', 'top_roles', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class CareerRecommendationListSerializer(serializers.ModelSerializer):
    """Simplified serializer untuk list view."""
    
    class Meta:
        model = CareerRecommendation
        fields = [
            'id', 'resume', 'dominant_category', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class JobRoleSerializer(serializers.ModelSerializer):
    """Serializer untuk Job Role reference data."""
    
    class Meta:
        model = JobRole
        fields = [
            'id', 'role_title', 'category', 'description',
            'required_skills', 'salary_range', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
