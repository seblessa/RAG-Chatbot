from rest_framework import serializers  
from django.contrib.auth import get_user_model  
  
User = get_user_model()
  
class TokenVerificationSerializer(serializers.Serializer):  
    token = serializers.CharField()  

class UserDataSerializer(serializers.ModelSerializer):
    username=serializers.CharField(source="name")
    lastLogin=serializers.DateTimeField(source="previous_login", format="%d/%b/%Y")

    class Meta:  
        model = User  
        fields = ['email','image','username','lastLogin', 'is_superuser']
