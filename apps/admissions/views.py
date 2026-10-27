from rest_framework import generics
from rest_framework.serializers import BaseSerializer

from apps.admissions import selectors, services
from apps.admissions.serializers import (
    AdmissionDeadlineSerializer,
    AdmissionRequirementSerializer,
    ScholarshipSerializer,
)
from apps.core.permissions import IsAdminOrReadOnly


class AdmissionRequirementListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdminOrReadOnly]
    serializer_class = AdmissionRequirementSerializer

    def get_queryset(self):
        return selectors.list_requirements(program_code=self.request.query_params.get("program"))

    def perform_create(self, serializer: BaseSerializer) -> None:
        serializer.instance = services.create_requirement(**serializer.validated_data)


class AdmissionRequirementDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminOrReadOnly]
    serializer_class = AdmissionRequirementSerializer
    queryset = selectors.list_requirements()

    def perform_update(self, serializer: BaseSerializer) -> None:
        serializer.instance = services.update_requirement(
            requirement=serializer.instance, **serializer.validated_data
        )

    def perform_destroy(self, instance) -> None:
        services.delete_requirement(requirement=instance)


class AdmissionDeadlineListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdminOrReadOnly]
    serializer_class = AdmissionDeadlineSerializer

    def get_queryset(self):
        return selectors.list_upcoming_deadlines(
            program_code=self.request.query_params.get("program")
        )

    def perform_create(self, serializer: BaseSerializer) -> None:
        serializer.instance = services.create_deadline(**serializer.validated_data)


class AdmissionDeadlineDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminOrReadOnly]
    serializer_class = AdmissionDeadlineSerializer
    queryset = selectors.list_deadlines()

    def perform_update(self, serializer: BaseSerializer) -> None:
        serializer.instance = services.update_deadline(
            deadline=serializer.instance, **serializer.validated_data
        )

    def perform_destroy(self, instance) -> None:
        services.delete_deadline(deadline=instance)


class ScholarshipListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdminOrReadOnly]
    serializer_class = ScholarshipSerializer

    def get_queryset(self):
        return selectors.list_active_scholarships()

    def perform_create(self, serializer: BaseSerializer) -> None:
        serializer.instance = services.create_scholarship(**serializer.validated_data)


class ScholarshipDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminOrReadOnly]
    serializer_class = ScholarshipSerializer
    queryset = selectors.list_scholarships()

    def perform_update(self, serializer: BaseSerializer) -> None:
        serializer.instance = services.update_scholarship(
            scholarship=serializer.instance, **serializer.validated_data
        )

    def perform_destroy(self, instance) -> None:
        services.delete_scholarship(scholarship=instance)
