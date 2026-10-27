from rest_framework import serializers

from apps.assistant.models import Document


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["id", "title", "file", "visibility", "status", "error", "created_at"]
        read_only_fields = ["id", "status", "error", "created_at"]


class AskSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=2000, allow_blank=False, trim_whitespace=True)


class SourceSerializer(serializers.Serializer):
    title = serializers.CharField()
    document_id = serializers.IntegerField(allow_null=True)
    chunk_id = serializers.IntegerField(allow_null=True)


class AnswerSerializer(serializers.Serializer):
    text = serializers.CharField()
    grounded = serializers.BooleanField()
    sources = SourceSerializer(many=True)
