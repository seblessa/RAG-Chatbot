import uuid  
from django.shortcuts import redirect  
from django.contrib.auth import get_user_model  
# from django.core.mail import send_mail  
from django.conf import settings  
from rest_framework import status  
from rest_framework.decorators import api_view  
from rest_framework.response import Response  
# from .models import Profile  
from .serializers import TokenVerificationSerializer  
from rest_framework.views import APIView  
from rest_framework.permissions import IsAuthenticated  
from rest_framework_simplejwt.authentication import JWTAuthentication 
from rest_framework_simplejwt.views import TokenObtainPairView  
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer 
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.exceptions import AuthenticationFailed  
from rest_framework import permissions  
from django.utils import timezone
from .serializers import UserDataSerializer  

User = get_user_model()  
  
@api_view(['POST'])  
def register(request):  
    return Response({"ReturnMessage": "O registo está desligado. PFV contactar ITlabs se necessitar de conta.","status":False}, status=status.HTTP_404_NOT_FOUND)
    serializer = RegistrationSerializer(data=request.data)  
    if serializer.is_valid():  
        user = serializer.save()  
        user.is_active = False  
        user.save()  
        token = uuid.uuid4().hex
        profile = Profile.objects.get(user=user)  
        profile.verification_token = token  
        profile.save()  
        verification_link = f"{settings.FRONTEND_URL}/verify?token={token}" 
        print(verification_link) 
        # send_mail(  
        #     'Verify your email',  
        #     f'Click the link to verify your email: {verification_link}',  
        #     settings.DEFAULT_FROM_EMAIL,  
        #     [user.email],  
        #     fail_silently=False,  
        # )  
        return Response({"ReturnMessage": "Email de verificação enviado!","status":True}, status=status.HTTP_201_CREATED)  
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)  
  
@api_view(['POST'])  
def verify_email(request):  
    return
    # serializer = TokenVerificationSerializer(data=request.data)
    # if serializer.is_valid():  
    #     token = serializer.validated_data['token']  
    #     try:  
    #         profile = Profile.objects.get(verification_token=token) 
    #         if not profile.user.is_active: 
    #             profile.user.is_active = True  
    #             profile.user.save()  
    #         return Response({"detail": "Email verificado com sucesso."}, status=status.HTTP_200_OK)  
    #     except Profile.DoesNotExist:  
    #         return Response({"detail": "Token invalido."}, status=status.HTTP_400_BAD_REQUEST)  
    # return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)  


 
  
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):  
    @classmethod  
    def get_token(cls, user):  
        token = super().get_token(user)  
  
        token['email'] = user.email   
        return token  
    def validate(self, attrs):  
        try:  
            data = super().validate(attrs) 
            user = self.user  
            if user and user.is_authenticated:
                user.previous_login=user.last_login 
                user.last_login = timezone.now()  
                user.save()  
        except AuthenticationFailed as exc:  
            raise AuthenticationFailed({  
                'ReturnMessage': 'Não foi encontrada nenhum conta com as credenciais fornecidas.\n Nota que é necessário confirmar o email para fazer login.'  
            })  

        return data  
class CustomTokenObtainPairView(TokenObtainPairView):  
    permission_classes = (permissions.AllowAny,)  
    serializer_class = CustomTokenObtainPairSerializer

  
class CustomTokenVerify(APIView):  
    permission_classes = [IsAuthenticated]  
    authentication_classes = [JWTAuthentication]  
  
    def get(self, request):  
        return Response({"detail": "Token é valido."}, status=200)  

class UserProfileView(APIView):  
    permission_classes = [IsAuthenticated]  
  
    def get(self, request):  
        user = request.user  
        serializer = UserDataSerializer(user)  
        return Response(serializer.data)  