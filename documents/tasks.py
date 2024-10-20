from celery import shared_task
from .models import Document
from chatapp.models import ChatMessage, ChatError
from celery import signals, current_app
from chatapp.serializers import ChatMessageSerializer
from haystack_components.documents_pipeline.save_stores import delete_Qdrant_doc, delete_Osearch_doc
import traceback

@shared_task(queue="chat_app_queue")
def process_document(did):
    doc=Document.objects.get(id=did)
    if doc.status in [Document.PossibleStatus.PROCESSING, Document.PossibleStatus.PROCESSED]:
        return
    doc._process_pipeline()
    return

@shared_task(queue="chat_app_queue")
def process_message(chat_msg_id,doc_ids=[]):
    msg=ChatMessage.objects.get(id=chat_msg_id)
    if msg.status == ChatMessage.Message_status.PROCESSING:
        return
    else:
        msg.status=ChatMessage.Message_status.PROCESSING
        msg.save()
    try:
        msg.get_related_docs()
    except Exception as e:
        ChatError.objects.create(
            session=msg.session,
            message=msg,
            function="process_message",
            exception=e,
            traceback=traceback.format_exc()
        )
        msg.status=ChatMessage.Message_status.FAILED
        msg.save()
    return

@shared_task(queue="chat_app_queue")
def get_LLM_response(msg_id):
    msg=ChatMessage.objects.get(id=msg_id)
    if msg.status == ChatMessage.Message_status.CONTEXT_SELECTED:
        serialized=ChatMessageSerializer(msg)
        try:
            msg.get_response(serialized.data)
        except Exception as e:
            ChatError.objects.create(
                session=msg.session,
                message=msg,
                function="get_LLM_response",
                exception=e,
                traceback=traceback.format_exc()
            )
            msg.status=ChatMessage.Message_status.FAILED
            msg.save()
    return


@shared_task(queue="chat_app_queue")
def delete_from_qdrant(qdrant_db_id):
    # Implement the deletion logic for Qdrant
    print("CAUGHT - DELETE QDRANT, ", qdrant_db_id)
    delete_Qdrant_doc(qdrant_db_id)
    pass

@shared_task(queue="chat_app_queue")
def delete_from_opensearch(opensearch_db_id):
    # Implement the deletion logic for OpenSearch
    print("CAUGHT - DELETE OPENSEARCH, ", opensearch_db_id)
    delete_Osearch_doc(opensearch_db_id)
    pass