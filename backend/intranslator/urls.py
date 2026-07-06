"""
URL configuration for intranslator project.

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
from rest_framework.routers import DefaultRouter
from . import views
from intentString import views as intent_views
from intentString.views import LimoDirectView

router = DefaultRouter()
# Natural Intent용
router.register(r'NaturalIntent', intent_views.NaturalIntentViewSet, 'NaturalIntent')
# Network Intent용
router.register(r'NetworkIntent', intent_views.NetworkIntentViewSet, 'NetworkIntent') 
# Applciation Intent용
router.register(r'ApplicationIntent', intent_views.ApplicationIntentViewSet, 'ApplicationIntent') 

router.register(r'PolicyIntent', intent_views.NaturalIntentViewSet, 'PolicyIntent')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/limo/', LimoDirectView.as_view(), name='limo-direct'),
    path('api/', include(router.urls)),
]