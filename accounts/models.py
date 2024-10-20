from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager  
from django.db import models  
from django.contrib.auth.models import PermissionsMixin

class CustomUserManager(BaseUserManager):  
    def create_user(self, email, password=None, **extra_fields):  
        if not email:  
            raise ValueError('The Email field must be set')  
        email = self.normalize_email(email)  
        user = self.model(email=email, **extra_fields)  
        user.set_password(password)  
        user.save(using=self._db)  
        return user  

    def create_superuser(self, email, password=None, **extra_fields):  
        extra_fields.setdefault('is_staff', True)  
        extra_fields.setdefault('is_superuser', True)  
        extra_fields.setdefault('is_active', True)  

        if extra_fields.get('is_staff') is not True:  
            raise ValueError('Superuser must have is_staff=True.')  
        if extra_fields.get('is_superuser') is not True:  
            raise ValueError('Superuser must have is_superuser=True.')  

        return self.create_user(email, password, **extra_fields)  

class CustomUser(AbstractBaseUser, PermissionsMixin):  
    email = models.EmailField(unique=True)  
    is_active = models.BooleanField(default=False)  
    is_staff = models.BooleanField(default=False)  
    is_superuser = models.BooleanField(default=False)  
    date_joined = models.DateTimeField(auto_now_add=True, editable=False)

    objects = CustomUserManager()  

    USERNAME_FIELD = 'email'  
    REQUIRED_FIELDS = []  

    image=models.ImageField(default='static/img/nmacedo.jpg', upload_to='static/img/')
    name=models.TextField(default="Nuno Macedo")
    previous_login=models.DateTimeField(null=True)

    def __str__(self):  
        return self.email  

# class Profile(models.Model):  
#     user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)  
#     verification_token = models.CharField(max_length=64, blank=True)  
  
#     def __str__(self):  
#         return self.user.email  