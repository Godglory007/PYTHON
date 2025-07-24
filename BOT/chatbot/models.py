from django.db import models
from django.contrib.auth.models import User

class Utilisateur(models.Model):
    nom = models.CharField(max_length=10)
    password= models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)

    
class ChatBot(models.Model):
    user = models.ForeignKey(
      Utilisateur,  on_delete=models.CASCADE, related_name='GeminiUser', null=True
    )
    text_input = models.CharField(max_length=500)
    gemini_output = models.TextField(null=True, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    def __str__(self):
        return self.nom

    class Meta:
        app_label = 'chatbot'

    
