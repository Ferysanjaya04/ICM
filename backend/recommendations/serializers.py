from rest_framework import serializers
from .models import CareerRecommendation, TopRole, JobRole
from lib.feature2 import salary_metadata


class TopRoleSerializer(serializers.ModelSerializer):
    """Serializer untuk Top Role recommendations."""
    
    category_probability = serializers.FloatField(source='match_details.category_probability', read_only=True, allow_null=True, default=None)
    predicted_category = serializers.CharField(source='match_details.predicted_category', read_only=True, allow_null=True, default=None)
    skill_match_available = serializers.BooleanField(source='match_details.skill_match_available', read_only=True, allow_null=True, default=None)
    skill_match_status = serializers.CharField(source='match_details.skill_match_status', read_only=True, default='legacy_unverified')
    required_skills = serializers.JSONField(source='match_details.required_skills', read_only=True, allow_null=True, default=None)
    matched_skills = serializers.JSONField(source='match_details.matched_skills', read_only=True, allow_null=True, default=None)
    missing_skills = serializers.JSONField(source='match_details.missing_skills', read_only=True, allow_null=True, default=None)
    source = serializers.CharField(source='match_details.source', read_only=True, allow_null=True, default=None)

    requirements_status = serializers.CharField(source='match_details.requirements_status', read_only=True, default='unknown')
    specialization_status = serializers.CharField(source='match_details.specialization_status', read_only=True, default='unknown')
    salary_metadata = serializers.JSONField(source='match_details.salary_metadata', read_only=True, allow_null=True, default=None)
    skill_evidence = serializers.JSONField(source='match_details.skill_evidence', read_only=True, allow_null=True, default=None)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not instance.match_details:
            # Old rows lack the original requirements/evidence snapshot. Preserve
            # their raw metric explicitly, without presenting it as verified coverage.
            data['legacy_match_percentage'] = data['match_percentage']
            data['match_percentage'] = None
            data['skill_match_available'] = False
            data['skill_match_status'] = 'legacy_unverified'
        details = instance.match_details or {}
        data['requirements_status'] = details.get('requirements_status') or (
            'known' if details.get('skill_match_available') and details.get('required_skills') else 'unknown'
        )
        # Read saved metadata only. Legacy values are retained separately, never
        # backfilled by rerunning the model or loading today's reference dataset.
        saved_salary = details.get('salary_metadata')
        if not saved_salary or saved_salary.get('status') != 'verified' or not all(
            saved_salary.get(key) for key in ('currency', 'payment_period', 'source')
        ) or not (saved_salary.get('market') or saved_salary.get('location')):
            data['salary_metadata'] = salary_metadata(instance.salary_range, details.get('reference')) if not saved_salary else {**saved_salary, 'status': 'unknown'}
            if instance.salary_range:
                data['legacy_salary_range'] = instance.salary_range
            data['salary_range'] = ''
        return data

    class Meta:
        model = TopRole
        fields = [
            'id', 'role_title', 'category', 'match_percentage',
            'rank', 'salary_range', 'category_probability', 'predicted_category',
            'skill_match_available', 'skill_match_status', 'required_skills',
            'matched_skills', 'missing_skills', 'source', 'match_details',
            'requirements_status', 'specialization_status', 'salary_metadata', 'skill_evidence',
        ]
        read_only_fields = ['id', 'rank']


class CareerRecommendationSerializer(serializers.ModelSerializer):
    """Serializer untuk Career Recommendation dengan nested TopRoles."""
    
    top_roles = TopRoleSerializer(many=True, read_only=True)
    extraction_quality = serializers.SerializerMethodField()

    def get_extraction_quality(self, instance):
        from resumes.extraction import unknown_extraction_quality
        summary = instance.profile_summary if isinstance(instance.profile_summary, dict) else {}
        return summary.get('extraction_quality') or unknown_extraction_quality()
    
    class Meta:
        model = CareerRecommendation
        fields = [
            'id', 'resume', 'dominant_category', 'profile_summary',
            'detected_skills', 'learning_path', 'top_roles', 'created_at', 'extraction_quality'
        ]
        read_only_fields = ['id', 'created_at']


class CareerRecommendationListSerializer(CareerRecommendationSerializer):
    """History preserves the same saved role/evidence snapshots as detail."""


class JobRoleSerializer(serializers.ModelSerializer):
    """Serializer untuk Job Role reference data."""
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['salary_metadata'] = salary_metadata(instance.salary_range, {
            'dataset': 'database JobRole', 'record_id': str(instance.pk),
        })
        if instance.salary_range:
            data['legacy_salary_range'] = instance.salary_range
        data['salary_range'] = ''
        return data

    class Meta:
        model = JobRole
        fields = [
            'id', 'role_title', 'category', 'description',
            'required_skills', 'salary_range', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
