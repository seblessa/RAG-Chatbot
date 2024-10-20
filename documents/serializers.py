from rest_framework import serializers
from .models import Document, Section, Page
from django.utils.encoding import smart_str
import os
from django.conf import settings
import json

http_url=settings.BACKEND_URL


class DocumentSerializer(serializers.ModelSerializer):
    owner = serializers.SlugRelatedField('email', read_only=True)
    status = serializers.CharField(source='get_status_display', read_only=True)
    # filename = serializers.CharField(source='filename', read_only=True)
    # finalized = serializers.DateTimeField(format="%d/%b/%Y %H:%M", source="docx_generated_stamp")

    def to_representation(self, instance):
        # self.fields['audio_file'].context['pipeline_id'] = instance.id
        # self.fields['transcription_document'].context['pipeline_id'] = instance.id
        representation = super().to_representation(instance)
        return representation

    class Meta:
        model = Document
        fields=["id","filename","status","owner"]

class PageSerializer(serializers.ModelSerializer):
    parent=DocumentSerializer(read_only=True)
    class Meta:
        model = Page
        fields=["page_number","parent"]

class SectionSerializer(serializers.ModelSerializer):
    parent=PageSerializer(read_only=True)
    extracted_information=serializers.SerializerMethodField()

    def get_extracted_information(self, instance):
        return json.loads(instance.extracted_information)
    class Meta:
        model = Section
        fields=["id","parent","raw_content","extracted_information", "num_tokens"]