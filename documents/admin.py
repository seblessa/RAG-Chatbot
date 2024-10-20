from django.contrib import admin
from .models import *
# Register your models here.
admin.site.register(Document)
admin.site.register(Page)
admin.site.register(Section)
admin.site.register(Section_NER)
admin.site.register(Section_intent)
admin.site.register(Phrase)