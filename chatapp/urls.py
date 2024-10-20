
from .views import get_createChat, send_getChatMessage, GetAllChats, GetChat, ClassifyMessage,get_docs
from django.urls import path

urlpatterns = [
    path("getID/", get_createChat.as_view()),
    path("send_getMessage/", send_getChatMessage.as_view()),

    path("GetAllChats/", GetAllChats.as_view()),
    path("GetChat/", GetChat.as_view()),
    path("ClassifyMessage/", ClassifyMessage.as_view()),
    path("get_docs/", get_docs.as_view())
]
