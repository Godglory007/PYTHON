from django.contrib import admin

from chatbot.models import ChatBot, Utilisateur

# Register your models here.
admin.site.register(ChatBot)     # enregistre le modèle ChatBot dans l’admin
admin.site.register(Utilisateur) # enregistre le modèle Utilisateur