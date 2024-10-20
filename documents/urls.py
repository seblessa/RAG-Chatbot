
from .views import get_all_docs, upload_chunk
from django.urls import path

urlpatterns = [
    # path('register/', register, name='register'),
    path("get_all/", get_all_docs),
    path("upload_chunk/", upload_chunk.as_view()),
]
