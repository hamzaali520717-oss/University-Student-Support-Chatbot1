from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.assistant import selectors, services
from apps.assistant.serializers import AnswerSerializer, AskSerializer, DocumentSerializer
from apps.core.permissions import IsAdminStaff


class DocumentListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdminStaff]
    serializer_class = DocumentSerializer

    def get_queryset(self):
        return selectors.list_documents()

    def perform_create(self, serializer: BaseSerializer) -> None:
        serializer.instance = services.create_document(**serializer.validated_data)


class DocumentDetailView(generics.RetrieveDestroyAPIView):
    permission_classes = [IsAdminStaff]
    serializer_class = DocumentSerializer

    def get_queryset(self):
        return selectors.list_documents()

    def perform_destroy(self, instance) -> None:
        services.delete_document(document=instance)


class ReindexDocumentView(APIView):
    permission_classes = [IsAdminStaff]

    def post(self, request: Request, pk: int) -> Response:
        document = generics.get_object_or_404(selectors.list_documents(), pk=pk)
        document = services.reindex_document(document=document)
        return Response(DocumentSerializer(document).data, status=status.HTTP_202_ACCEPTED)


class AskView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ask"

    def post(self, request: Request) -> Response:
        serializer = AskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        question = serializer.validated_data["question"]
        student = selectors.get_asking_student(user=request.user)
        answer = services.answer_question(
            question=question,
            student=student,
            include_personal_context=services.is_personal_question(question),
        )
        return Response(AnswerSerializer(answer).data, status=status.HTTP_200_OK)
