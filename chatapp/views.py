from email.policy import default

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import status
from rest_framework.response import Response
import time
import json
import random
from django.db.models import Exists, OuterRef, Count

from .models import ChatInstance, RuleSet, ChatMessage
from .serializers import *

from haystack_components.pipeline import prompt_engineering_pipeline

# Create your views here.
class get_createChat(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, format=None):
        DEFAULT_RULESET = RuleSet.objects.filter(default_set=True).first()
        cid=request.GET.get('cid',None)
        if not ChatInstance.objects.filter(id=cid, owner=request.user).first():
            chat=ChatInstance.objects.create(id=cid, owner=request.user, rule_set=DEFAULT_RULESET)
            cid=chat.id
        return JsonResponse({"id":cid, "status": True})
    def post(self, request, format=None):
        return JsonResponse({"msg": "Method not allowed", "status": False},status=500)


class send_getChatMessage(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def get(self, request, format=None):
        message=ChatMessage.objects.filter(session__owner=request.user,id=request.GET.get("mid",0)).first()
        if not message:
            return JsonResponse({"msg": "Method not allowed", "status": False})
        msg_ser=ChatMessageSerializer(message)
        return JsonResponse({"status":True,"status_code":message.status,"response": message.response, "data":msg_ser.data},json_dumps_params={'ensure_ascii': False})
    def post(self, request, format=None):
        d = json.loads(request.body)
        # print(d)
        cid = d.get("chatid")
        if not ChatInstance.objects.filter(id=cid, owner=request.user).first():
            return JsonResponse({"status":False, "msg": "Chat not found!"})
        chat=ChatInstance.objects.filter(id=cid, owner=request.user).first()
        message=ChatMessage.objects.create(
            message=d.get("message"),
            session=chat
        )
        message.init_process()
        return JsonResponse({"status":True, "mid":message.id})


class GetAllChats(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [JWTAuthentication]
    def get(self, request, format=None):
        chats_with_messages = ChatInstance.objects.annotate(
            has_messages=Exists(
                ChatMessage.objects.filter(session=OuterRef('pk'))
            )
        ).filter(has_messages=True).order_by('-created_at')

        chats_with_messages_C = ChatInstance.objects.annotate(
            has_messages=Exists(
                ChatMessage.objects.filter(session=OuterRef('pk'))
            ),
            message_count=Count('messages')  # Assuming 'chatmessage' is the related name
        ).filter(has_messages=True).order_by("-created_at")
        chats=ChatInstance.objects.all().order_by("-created_at")
        data=ChatInstanceSerializer(chats_with_messages_C,many=True)
        return JsonResponse({"data":data.data})

class GetChat(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [JWTAuthentication]
    def get(self, request, format=None):
        chat=ChatInstance.objects.filter(id=request.GET.get("cid")).first()
        data = FullChatInstanceSerializer(chat)
        return JsonResponse({"data": data.data}, json_dumps_params={'ensure_ascii': False})

class ClassifyMessage(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [JWTAuthentication]

    def get(self, request, format=None):

        # time.sleep(10)
        message=ChatMessage.objects.filter(id=request.GET.get("mid"), session__owner=request.user).first()
        if not message:
            return JsonResponse({"status": False, "msg": "Invalid message ID or owner."})

        try:
            rating = int(request.GET.get("rating"))
            if not 1 <= rating <= 5:
                raise ValueError("Invalid rating")
        except (TypeError, ValueError):
            return JsonResponse({"status": False, "msg": "Invalid rating"})

        message.rate(rating)
        return JsonResponse({"status": True, "msg": "Rated"})

class get_docs(APIView):

    def post(self, request, format=None):
        query=request.data.get("query")
        result=prompt_engineering_pipeline(query)
        documents_list = []
        for doc in result['JoinDocuments']['documents']:
            doc_dict = {
                "id": str(doc.id),
                "content": doc.content,
                "meta": doc.meta,
                "score": doc.score,
            }
            documents_list.append(doc_dict)
        print(documents_list)
        return Response({"status": True, "documents": documents_list }, status=status.HTTP_200_OK)