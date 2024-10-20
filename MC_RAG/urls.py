"""
URL configuration for MC_RAG project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path(settings.URL_PREFIX+'api/admin/', admin.site.urls),
    # path("api/", include('frontend.urls')),
    path(settings.URL_PREFIX+'api/accounts/', include('accounts.urls')),
    path(settings.URL_PREFIX+'api/documents/', include('documents.urls')),
    path(settings.URL_PREFIX+'api/chats/', include('chatapp.urls')),
    # path('api/monitor/', include('monitoring.urls')),
    path("api/get_docs/", include('chatapp.urls')),
]

urlpatterns += [
] + static(settings.URL_PREFIX+'api'+settings.STATIC_URL, document_root=settings.STATIC_ROOT)