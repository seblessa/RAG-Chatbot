from django.utils import timezone
from django.db import models
from haystack_components.pipeline import document_processor_pipeline, pdf_layout_process, new_doc_pipeline
from haystack_components.documents_pipeline.save_stores import get_os_doc
import json
import os
from celery import current_app
import tiktoken
# Create your models here.
class Chunks(models.Model):
    '''
    Used to control IDs for chunking - may be further used in the future for debugging.
    '''
    originalFile=models.CharField(max_length=255)


class Document(models.Model):
    class PossibleStatus(models.IntegerChoices):
        FAILED = -1
        CREATED = 0
        PROCESSED = 1

        IN_PROCESSING_Q = 2
        PROCESSING = 3
        # AUDIO_UPLOADED=4
        # TRANSCRIPTION_STARTED=5
        # TRANSCRIPTION_COMPLETE=6
        # GPT_POST_PROCESSING=7

    file=models.FileField(upload_to="protected_static/documents/")
    owner=models.ForeignKey("accounts.CustomUser", on_delete=models.CASCADE)
    status=models.IntegerField(choices=PossibleStatus, default=PossibleStatus.CREATED)

    created=models.DateTimeField(auto_now_add=True)
    # last_stamp=models.DateTimeField(null=True, blank=True)

    processing_started=models.DateTimeField(null=True, blank=True)
    processing_finished=models.DateTimeField(null=True, blank=True)
    shared_with=models.ManyToManyField("accounts.CustomUser", blank=True, related_name="documents_shared_with")

    raw_pdf_process=models.TextField(blank=True)

    def init_process(self):
        self.status=self.PossibleStatus.IN_PROCESSING_Q
        self.save()
        current_app.send_task("documents.tasks.process_document", (self.id,), queue="chat_app_queue")
        #send_task
        return

    def _process_pipeline(self):
        self.processing_started=timezone.now()
        self.status=self.PossibleStatus.PROCESSING
        self.save()

        doc_result=new_doc_pipeline(str(self.file),self.id)

        encoder=tiktoken.get_encoding("cl100k_base")
        print(doc_result["Save_QD"]["documents"])
        # return doc_result
        for section_content in doc_result["Save_QD"]["documents"]["sections"]:
            sec=self.__create_pages_and_section(section_content,encoder)
        for phrase_content in doc_result["Save_QD"]["documents"]["phrases"]:
            sec=Section.objects.get(Osearch_db_id=phrase_content.meta["source_id"], parent__parent=self)
            Phrase.objects.create(
                parent=sec,
                raw_content=phrase_content.content,
                Qdrant_db_id=phrase_content.id,
                num_tokens=self.num_tokens_from_string(phrase_content.content,encoder),
                phrase_order=Phrase.objects.filter(parent=sec.id).count()+1
            )
        self.processing_finished=timezone.now()
        self.status=self.PossibleStatus.PROCESSED
        self.save()

        return
    
    def __create_pages_and_section(self, osdoc,encoder):
        page,created=Page.objects.get_or_create(parent=self, page_number=osdoc.meta["page_number"])
        if "extracted_info" in osdoc.meta.keys():
            ex_info=json.loads(osdoc.meta["extracted_info"])
        else:
            ex_info={}
        sec=Section.objects.create(
            parent=page,
            Osearch_db_id=osdoc.id,
            raw_content=osdoc.content,
            num_tokens=self.num_tokens_from_string(osdoc.content, encoder),
            section_order=Section.objects.filter(parent=page.id).count()+1,
            extracted_information=json.dumps(ex_info)
        )
        if "NER" in ex_info.keys():
            for i in ex_info["NER"]:
                for key,val in i.items():
                    Section_NER.objects.create(
                        section=sec,
                        expression=key,
                        classification=val
                    )
        if "Intenção" in ex_info.keys():
            for intent in ex_info["Intenção"]:
                Section_intent.objects.create(
                    section=sec,
                    intent=intent
                )
        return sec
    def _get_raw_pdf_process_json(self):
        self.raw_pdf_process=json.dumps(pdf_layout_process(str(self.file),self.id)["Splitter"]["result"],ensure_ascii=False)
        self.save()
        return

    def num_tokens_from_string(self,string: str, encoder) -> int:
        num_tokens = len(encoder.encode(string))
        return num_tokens

    @property
    def filename(self):
        return os.path.basename(self.file.name)
    
    def __str__(self) -> str:
        return self.filename
    
class Page(models.Model):
    parent=models.ForeignKey("Document",on_delete=models.CASCADE)
    page_number=models.IntegerField(default=1)

    def __str__(self) -> str:
        return f"{self.parent} page #{self.page_number}"
    
    class Meta:
        ordering=["parent","page_number"]


class Section(models.Model):
    parent=models.ForeignKey("Page",on_delete=models.CASCADE)
    Osearch_db_id=models.CharField(max_length=255, null=True, blank=True)

    raw_content=models.TextField(blank=True)
    markdown_content=models.TextField(blank=True)
    html_content=models.TextField(blank=True)

    section_order=models.IntegerField(default=1)

    extracted_information=models.TextField(blank=True)
    num_tokens=models.IntegerField(default=0)
    def __str__(self) -> str:
        return f"{self.parent} section #{self.section_order}"
    
    class Meta:
        ordering=("parent","section_order")
class Section_intent(models.Model):
    section=models.ForeignKey("Section",on_delete=models.CASCADE)
    intent=models.CharField(max_length=255)

    def __str__(self) -> str:
        return self.intent
    
    @classmethod
    def get_intent_list(cls):
        return list(cls.objects.values_list('intent', flat=True).distinct())

class Section_NER(models.Model):
    section=models.ForeignKey("Section",on_delete=models.CASCADE)
    expression=models.CharField(max_length=255)
    classification=models.CharField(max_length=255)
    
    def __str__(self) -> str:
        return f"{self.classification} - {self.expression}"

    @classmethod
    def get_NER_list(cls):
        return list(cls.objects.values_list('classification', flat=True).distinct())
    
class Phrase(models.Model):
    parent=models.ForeignKey("Section",on_delete=models.CASCADE)
    Qdrant_db_id=models.CharField(max_length=255, null=True, blank=True)
    raw_content=models.TextField(blank=True)
    phrase_order=models.IntegerField(default=1)
    num_tokens = models.IntegerField(default=0)
    def __str__(self) -> str:
        return f"{self.parent} phrase #{self.phrase_order}"
    
    class Meta:
        ordering=("parent", "phrase_order")

class DocImage(models.Model):
    parent=models.ForeignKey("Section",on_delete=models.CASCADE)
    file=models.FileField(upload_to="protected_static/document_images/")