from django.db import models
from django.contrib.auth.models import User
import os

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
    anomalies = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    audit_type = models.CharField(max_length=100, blank=True)  # Type d'audit (financier, conformité, etc.)
    def __str__(self):
        return self.nom

    class Meta:
        app_label = 'chatbot'

class UserFile(models.Model):
    FILE_TYPES = [
        ('document', 'Document'),
        ('image', 'Image'),
        ('spreadsheet', 'Tableur'),
        ('presentation', 'Présentation'),
        ('other', 'Autre'),
    ]
    
    user = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='user_files/')
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=20, choices=FILE_TYPES, default='other')
    file_size = models.IntegerField(help_text="Taille en bytes")
    description = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.file_name} - {self.user.nom}"
    
    def get_file_extension(self):
        return os.path.splitext(self.file_name)[1].lower()
    
    def get_file_size_mb(self):
        return round(self.file_size / (1024 * 1024), 2)
    
    def is_image(self):
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']
        return self.get_file_extension() in image_extensions
    
    class Meta:
        ordering = ['-uploaded_at']

    
