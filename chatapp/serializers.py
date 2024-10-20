from rest_framework import serializers
from .models import ContextSelection, SelectedDocuments, ChatMessage,ChatInstance, OriginalScores
from documents.serializers import SectionSerializer

class OriginalScoresSerializer(serializers.ModelSerializer):
    class Meta:
        model = OriginalScores
        fields = ['score', 'origin']

class SelectedDocumentsSerializer(serializers.ModelSerializer):
    section = SectionSerializer(read_only=True)
    original_scores = OriginalScoresSerializer(many=True, read_only=True)

    class Meta:
        model = SelectedDocuments
        fields = ['section', 'score', 'original_scores']


class ContextSelectionSerializer(serializers.ModelSerializer):
    selected_documents = serializers.SerializerMethodField()

    class Meta:
        model = ContextSelection
        fields = ['created_at', 'total_tokens','KS_parameters','VS_parameters', 'selected_documents']

    def get_selected_documents(self, obj):
        selected_documents = obj.selected_documents.all().order_by('-score')
        return SelectedDocumentsSerializer(selected_documents, many=True).data


class ChatMessageSerializer(serializers.ModelSerializer):
    used_context = ContextSelectionSerializer()
    created_at=serializers.DateTimeField(format="%d/%m/%Y %H:%M:%S")
    reply_received_stamp=serializers.DateTimeField(format="%d/%m/%Y %H:%M:%S")
    class Meta:
        model = ChatMessage
        fields = ['id','message', 'response', 'session', 'created_at', 'status', 'used_context','reply_received_stamp','response_rating']

class ChatInstanceSerializer(serializers.ModelSerializer):
    owner = serializers.CharField(source="owner.name", read_only=True)
    message_count=serializers.IntegerField(read_only=True)
    class Meta:
        model = ChatInstance
        fields = ['id', 'owner', 'created_at', 'updated_at','message_count']

class FullChatInstanceSerializer(serializers.ModelSerializer):
    owner = serializers.CharField(source="owner.name", read_only=True)
    messages=ChatMessageSerializer(many=True)
    class Meta:
        model = ChatInstance
        fields = ['id', 'owner', 'created_at', 'updated_at', 'messages']
