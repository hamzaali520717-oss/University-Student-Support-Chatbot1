from rest_framework import serializers

from apps.academics.models import Program
from apps.admissions.models import AdmissionDeadline, AdmissionRequirement, Scholarship


class AdmissionRequirementSerializer(serializers.ModelSerializer):
    program = serializers.SlugRelatedField(
        slug_field="code", queryset=Program.objects.all()
    )

    class Meta:
        model = AdmissionRequirement
        fields = ["id", "program", "title", "description", "created_at"]
        read_only_fields = ["id", "created_at"]


class AdmissionDeadlineSerializer(serializers.ModelSerializer):
    program = serializers.SlugRelatedField(
        slug_field="code", queryset=Program.objects.all()
    )

    class Meta:
        model = AdmissionDeadline
        fields = ["id", "program", "label", "date", "created_at"]
        read_only_fields = ["id", "created_at"]


class ScholarshipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scholarship
        fields = [
            "id",
            "name",
            "description",
            "amount",
            "eligibility_criteria",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
