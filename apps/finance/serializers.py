from decimal import Decimal

from rest_framework import serializers

from apps.academics.models import Program
from apps.accounts.models import StudentProfile
from apps.finance.models import FeeStatus, FeeStructure


class FeeStructureSerializer(serializers.ModelSerializer):
    program = serializers.SlugRelatedField(slug_field="code", queryset=Program.objects.all())

    class Meta:
        model = FeeStructure
        fields = ["id", "program", "semester", "amount", "breakdown", "created_at"]
        read_only_fields = ["id", "created_at"]


class FeeStatusSerializer(serializers.ModelSerializer):
    student = serializers.SlugRelatedField(
        slug_field="registration_no", queryset=StudentProfile.objects.all()
    )

    class Meta:
        model = FeeStatus
        fields = [
            "id",
            "student",
            "semester",
            "amount_due",
            "amount_paid",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]


class RecordPaymentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0.01")
    )
