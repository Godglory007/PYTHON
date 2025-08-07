"""
URL configuration for BOT project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""

from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from chatbot import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('ask_question/', views.ask_question, name="ask_question"),
    path("chatbot/", views.chatbot_page, name="chatbot_page"),
    path('connexion/', views.connexion, name="connexion"),
    path('inscription/', views.inscription, name="inscription"),
    path('', views.connexion, name="Connexion "),  # Ajout du chemin racine
    
    # URLs pour la gestion des fichiers
    path('upload_file/', views.upload_file, name="upload_file"),
    path('get_user_files/', views.get_user_files, name="get_user_files"),
    path('download_file/<int:file_id>/', views.download_file, name="download_file"),
    path('delete_file/<int:file_id>/', views.delete_file, name="delete_file"),
    path('get_file_preview/<int:file_id>/', views.get_file_preview, name="get_file_preview"),
]

# Ajouter les URLs pour servir les fichiers média en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



