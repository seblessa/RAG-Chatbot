from django.urls import path  
from .views import verify_email, CustomTokenObtainPairView, CustomTokenVerify, UserProfileView
from rest_framework_simplejwt.views import TokenVerifyView, TokenRefreshView

urlpatterns = [  
    # path('register/', register, name='register'),  
    path('verify_email/', verify_email, name='verify'),  
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'), 
    path("get_self/", UserProfileView.as_view(), name="get_user_data"),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),    
    path('token/verify/', CustomTokenVerify.as_view(), name='token_verify'),  
]  
