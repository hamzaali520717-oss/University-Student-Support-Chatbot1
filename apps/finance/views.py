from rest_framework import generics, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.views import APIView

from apps.core.permissions import IsAdminOrReadOnly, IsAdminStaff, IsStudent
from apps.finance import selectors, services
from apps.finance.permissions import IsOwnFeeStatus
from apps.finance.serializers import (
    FeeStatusSerializer,
    FeeStructureSerializer,
    RecordPaymentSerializer,
)


class FeeStructureListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdminOrReadOnly]
    serializer_class = FeeStructureSerializer

    def get_queryset(self):
        return selectors.list_fee_structures(program_code=self.request.query_params.get("program"))

    def perform_create(self, serializer: BaseSerializer) -> None:
        serializer.instance = services.create_fee_structure(**serializer.validated_data)


class FeeStructureDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminOrReadOnly]
    serializer_class = FeeStructureSerializer
    queryset = selectors.list_fee_structures()

    def perform_update(self, serializer: BaseSerializer) -> None:
        serializer.instance = services.update_fee_structure(
            fee_structure=serializer.instance, **serializer.validated_data
        )

    def perform_destroy(self, instance) -> None:
        services.delete_fee_structure(fee_structure=instance)


class MyFeeStatusListView(generics.ListAPIView):
    permission_classes = [IsStudent]
    serializer_class = FeeStatusSerializer

    def get_queryset(self):
        return selectors.list_student_fee_statuses(student=self.request.user.student_profile)


class MyFeeStatusDetailView(generics.RetrieveAPIView):
    permission_classes = [IsStudent, IsOwnFeeStatus]
    serializer_class = FeeStatusSerializer

    def get_queryset(self):
        return selectors.list_student_fee_statuses(student=self.request.user.student_profile)


class FeeStatusListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdminStaff]
    serializer_class = FeeStatusSerializer

    def get_queryset(self):
        return selectors.list_fee_statuses()

    def perform_create(self, serializer: BaseSerializer) -> None:
        serializer.instance = services.create_fee_status(**serializer.validated_data)


class FeeStatusDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAdminStaff]
    serializer_class = FeeStatusSerializer
    queryset = selectors.list_fee_statuses()

    def perform_update(self, serializer: BaseSerializer) -> None:
        serializer.instance = services.update_fee_status(
            fee_status=serializer.instance, **serializer.validated_data
        )


class RecordFeePaymentView(APIView):
    permission_classes = [IsAdminStaff]

    def post(self, request: Request, pk: int) -> Response:
        fee_status = generics.get_object_or_404(selectors.list_fee_statuses(), pk=pk)
        serializer = RecordPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = services.record_payment(
            fee_status=fee_status, amount=serializer.validated_data["amount"]
        )
        return Response(FeeStatusSerializer(updated).data, status=status.HTTP_200_OK)
