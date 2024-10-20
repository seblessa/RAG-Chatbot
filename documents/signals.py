from django.db.models.signals import pre_delete
from django.dispatch import receiver
from .models import Section, Phrase
from .tasks import delete_from_qdrant, delete_from_opensearch

@receiver(pre_delete, sender=Section)
def handle_section_delete(sender, instance, **kwargs):
    if instance.Osearch_db_id:
        delete_from_opensearch.delay(instance.Osearch_db_id)
    # raise Exception("THIS IS A TEST")

@receiver(pre_delete, sender=Phrase)
def handle_phrase_delete(sender, instance, **kwargs):
    if instance.Qdrant_db_id:
        delete_from_qdrant.delay(instance.Qdrant_db_id)

    # raise Exception("THIS IS A TEST")
