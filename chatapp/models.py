from celery import current_app
from django.db import models

from haystack_components.askLLM.GPT import MAX_CONTEXT_TOKENS
from haystack_components.pipeline import prompt_engineering_pipeline, ask_LLM_with_context
from documents.models import Section, Phrase
from django.utils import timezone
import json, os

MAX_CONTEXT_TOKENS=int(os.getenv("MAX_CONTEXT_TOKENS",4000))
MIN_ORIGINAL_SCORE=float(os.getenv("MIN_ORIGINAL_SCORE",0.0))
class RuleSet(models.Model):
    system_message = models.TextField()
    default_set=models.BooleanField(default=False)
# Create your models here.
class ChatInstance(models.Model):
    class ChatStatus(models.IntegerChoices):
        WAITING_FOR_ASSITANT = 0
        PROCESSING = 1
        WAITING_FOR_USER = 2

    owner=models.ForeignKey("accounts.CustomUser", on_delete=models.CASCADE)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    rule_set=models.ForeignKey("RuleSet", related_name="chat_instance_set", on_delete=models.SET_NULL, null=True)
    status=models.IntegerField(choices=ChatStatus, default=ChatStatus.WAITING_FOR_USER)

    def get_last5(self):
        messages=self.messages.all().exclude(status=ChatMessage.Message_status.FAILED).order_by("-created_at")
        # mids=messages.values_list("id",flat=True)
        return self.messages.filter(id__in=messages[:5].values_list("id",flat=True)).order_by("created_at")


class ChatMessage(models.Model):
    # class PossibleSources(models.IntegerChoices):
    #     ASSISTANT = 0
    #     USER = 1
    class Message_status(models.IntegerChoices):
        FAILED = -1
        INITIALIZED = 0
        FINALIZED = 1
        PROCESSING = 2
        CONTEXT_SELECTED = 3

    # source=models.IntegerField(choices=PossibleSources)
    message=models.TextField()
    response=models.TextField()
    response_rating=models.IntegerField(default=0)
    session=models.ForeignKey("ChatInstance", related_name="messages", on_delete=models.CASCADE)
    created_at=models.DateTimeField(auto_now_add=True)

    context_selected_stamp=models.DateTimeField(null=True,blank=True)
    reply_received_stamp=models.DateTimeField(null=True,blank=True)

    status=models.IntegerField(choices=Message_status, default=Message_status.INITIALIZED)

    used_context=models.ForeignKey("ContextSelection", null=True, blank=True, on_delete=models.SET_NULL)
    needs_context_selection=models.BooleanField(default=False)

    def init_process(self):
        current_app.send_task("documents.tasks.process_message", (self.id,), queue="chat_app_queue")
        return

    def get_last_5_messages(self, as_json=False):
        session= self.session
        last_messages=session.get_last5()
        ret_json=[]
        for i in last_messages:
            ret_json.append({"role":"user","content":i.message})
            ret_json.append({"role":"assistant","content":i.response})
        # ret_json=[{"role":"user","content":i.message},{"role":"assistant","content":i.response} for i in last_messages]
        ret_json.append({"role":"user","content":self.message})
        if as_json:
            return ret_json
        return json.dumps(ret_json, ensure_ascii=False)
    def get_related_docs(self):
        #Get the last 5 messages and send to the pipeline
        results=prompt_engineering_pipeline(self.get_last_5_messages())

        #create a context selection
        context=ContextSelection.objects.create()

        #save re-engineered search parameters
        context.KS_parameters="; ".join([" ".join(entry) for entry in results["KS"]["search_params"]])
        context.VS_parameters="; ".join(results["VS"]["search_params"])

        #save original scores
        ks_scores=results["KS"]["original_scores"]
        vs_scores=results["VS"]["original_scores"]

        self.used_context=context
        used_tokens=0
        for result in results["JoinDocuments"]["documents"]:
            if "source_id" in result.meta.keys():#means it is a phrase
                original_score=vs_scores[result.id]
                origin="VS"
                try:
                    section = Section.objects.filter(Osearch_db_id=result.meta["source_id"]).first()
                except:
                    phrase=Phrase.objects.get(id=result.id)
                    section=phrase.parent
            else:#it is a section
                original_score=ks_scores[result.id]
                origin="KS"
                section=Section.objects.filter(Osearch_db_id=result.id).first()
            if context.selected_documents.filter(section=section).exists():
                #If already exists, update the score if it is higher; save the original score
                sel=context.selected_documents.filter(section=section).first()
                OriginalScores.objects.create(
                    selection_instance=sel,
                    score=original_score,
                    origin=origin
                )
                if sel.score < result.score:
                    sel.score=result.score
                    sel.save()
            else:
                #if doesn't exist, create a new selected documents instance and save computed and original score
                if original_score < MIN_ORIGINAL_SCORE:
                    continue
                used_tokens+=section.num_tokens
                sel=SelectedDocuments.objects.create(
                    section=section,
                    score=result.score,
                )
                OriginalScores.objects.create(
                    selection_instance=sel,
                    score=original_score,
                    origin=origin
                )
                context.selected_documents.add(sel)

        self.status=self.Message_status.CONTEXT_SELECTED
        self.context_selected_stamp=timezone.now()
        self.save()
        context.total_tokens=min(used_tokens,MAX_CONTEXT_TOKENS)
        context.save()
        current_app.send_task("documents.tasks.get_LLM_response", (self.id,), queue="chat_app_queue")
        return

    def get_response(self,serialized_context):
        serialized_history=self.get_last_5_messages(as_json=True)
        response=ask_LLM_with_context(serialized_history, serialized_context)
        print(response)
        self.response=response['LLM']["response"]
        self.reply_received_stamp=timezone.now()
        self.status = self.Message_status.FINALIZED
        self.save()
        return

    def build_context(self):
        return

    '''External methods'''
    def rate(self,rating):
        self.response_rating=rating
        self.save()
        return
    class Meta:
        ordering=["created_at"]


class ContextSelection(models.Model):
    created_at=models.DateTimeField(auto_now_add=True)
    total_tokens=models.IntegerField(default=0)
    selected_documents=models.ManyToManyField("SelectedDocuments", blank=True)
    KS_parameters=models.TextField(blank=True)
    VS_parameters=models.TextField(blank=True)

    raw_selection=models.TextField(blank=True)

class SelectedDocuments(models.Model):
    # document=models.ForeignKey("documents.Document", on_delete=models.CASCADE)
    section=models.ForeignKey("documents.Section", on_delete=models.CASCADE)
    score=models.FloatField(default=0)

class OriginalScores(models.Model):
    selection_instance=models.ForeignKey("SelectedDocuments", on_delete=models.CASCADE, related_name="original_scores")
    score=models.FloatField()
    origin=models.CharField(max_length=100)


class ChatError(models.Model):
    session=models.ForeignKey("ChatInstance", on_delete=models.SET_NULL, null=True)
    message=models.ForeignKey("ChatMessage", on_delete=models.SET_NULL, null=True)
    function=models.CharField(max_length=100)
    exception=models.CharField(max_length=100)
    traceback=models.TextField()

    timestamp=models.DateTimeField(auto_now_add=True)