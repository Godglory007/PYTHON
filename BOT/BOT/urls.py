"""
URL configuration for BOT project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""

from django.contrib import admin
from django.urls import path
from chatbot import views

urlpatterns = [
    path('', views.chatbot_page, name="home"),  # Page d'accueil : http://127.0.0.1:8000/
    path('ask_question/', views.ask_question, name="ask_question"),
    path('chatbot/', views.chatbot_page, name="chatbot_page"),
    path('connexion/', views.connexion, name="connexion"),
    path('inscription/', views.inscription, name="inscription"),
    path('admin/', admin.site.urls),
]


