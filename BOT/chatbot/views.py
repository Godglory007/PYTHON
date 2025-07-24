from django.http import JsonResponse
from django.shortcuts import render
import os
from django.shortcuts import render,redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.conf import settings
from django.http import JsonResponse
import json
import google.generativeai as genai
from .models import ChatBot,Utilisateur
from chatbot.models import ChatBot, Utilisateur

# Create your views here.
def connexion(request):
    print("Début de la fonction connexion")
    if request.method == 'POST':
        nom = request.POST.get('username')
        password = request.POST.get('password1')
        print(f"Tentative de connexion pour l'utilisateur : {nom}")
        print(f"Données POST reçues : {request.POST}")

        try:
            user = Utilisateur.objects.get(nom=nom)
            if check_password(password, user.password):
                # Stockage des informations de session
                request.session['user_id'] = str(user.id)
                request.session['username'] = user.nom
                request.session.save()  # Force la sauvegarde de la session
                
                print("Session créée avec succès:")
                print(f"user_id: {request.session.get('user_id')}")
                print(f"username: {request.session.get('username')}")
                
                # Redirection avec chemin absolu
                response = redirect('/chatbot/')
                print(f"Redirection vers: {response.url}")
                return response
            else:
                print("Mot de passe incorrect")
                messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
                return redirect('/')
        except Utilisateur.DoesNotExist:
            print("Utilisateur non trouvé")
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
            return redirect('/')
        except Exception as e:
            print(f"Erreur inattendue: {str(e)}")
            messages.error(request, "Une erreur est survenue. Veuillez réessayer.")
            return redirect('/')
    return render(request, 'connexion.html')

def inscription(request):
    if request.method == 'POST':
        nom = request.POST.get('username')
        password = request.POST.get('password')
        confirmpassword = request.POST.get('confirmpassword')
        if Utilisateur.objects.filter(nom=nom).exists():
            messages.error(request, "Nom d'utilisateur déjà pris.")
            return redirect('inscription')
        else:
            if password != confirmpassword:
                messages.error(request, "Les mots de passe ne correspondent pas.")
                return redirect('inscription')
            else:
                Utilisateur.objects.create(nom=nom, password=make_password(password))
                messages.success(request, "Inscription réussie. Vous pouvez maintenant vous connecter.")
            return redirect('connexion')
    return render(request, 'inscription.html')


def ask_question(request):
    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée"}, status=405)

    try:
        # Vérification de l'authentification
        user_id = request.session.get('user_id')
        if not user_id:
            return JsonResponse({"error": "Session expirée. Veuillez vous reconnecter."}, status=401)

        # Récupération et validation des données
        try:
            data = json.loads(request.body.decode("utf-8"))
            text = data.get("text", "").strip()
            if not text:
                return JsonResponse({"error": "Le message est vide."}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Format de données invalide."}, status=400)

        # Récupération de l'utilisateur et de son historique
        try:
            user = Utilisateur.objects.get(id=user_id)
            # Récupérer les 5 dernières conversations pour le contexte du bot
            recent_conversations = ChatBot.objects.filter(user=user).order_by('-created_at')

            
            # Construire le prompt avec l'historique des conversations
            prompt = "Voici l'historique des conversations précédentes pour le contexte :\n\n"
            
            for conv in reversed(recent_conversations):
                prompt += f"Question précédente : {conv.text_input}\n"
                prompt += f"Réponse précédente : {conv.gemini_output}\n\n"
            
            # Ajouter la nouvelle question avec le contexte
            prompt += f"""En tenant compte de cet historique, voici la nouvelle question : {text}

Instructions :
1. Si la question actuelle est liée à une conversation précédente, utilise ce contexte pour répondre.
2. Si tu fais référence à une conversation précédente, indique-le explicitement.
3. Reste cohérent avec les réponses précédentes.
4. Réponds toujours en français de manière professionnelle et polie."""

            # Vérification de la clé API
            api_key = settings.GEMINI_API_KEY
            if not api_key:
                return JsonResponse({"error": "Configuration du serveur incomplète."}, status=500)

            # Configuration et appel de l'API Gemini
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            # Envoyer le message avec tout le contexte
            response = model.generate_content(prompt)

            # Enregistrement du message
            ChatBot.objects.create(
                text_input=text,
                gemini_output=response.text,
                user=user
            )

            return JsonResponse({"response": response.text})

        except Exception as e:
            print(f"Erreur Gemini API : {str(e)}")
            return JsonResponse(
                {"error": "Désolé, je ne peux pas répondre pour le moment. Veuillez réessayer."}, 
                status=500
            )

    except Exception as e:
        print(f"Erreur inattendue : {str(e)}")
        return JsonResponse({"error": "Une erreur inattendue s'est produite."}, status=500)

def chatbot_page(request):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, "Veuillez vous connecter pour accéder au chatbot.")
        return redirect('/')
    try:
        user = Utilisateur.objects.get(id=user_id)
        # Récupérer l'historique complet pour la modal d'historique
        chat_history_all = ChatBot.objects.filter(user=user).order_by('-created_at')
        
        # Préparer l'historique complet pour la modal
        history_data_all = [{
            'message': chat.text_input,
            'response': chat.gemini_output,
            'timestamp': chat.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for chat in chat_history_all]
        
        context = {
            'username': user.nom,
            'chat_history': json.dumps([]),  # Liste vide pour le chat principal
            'chat_history_all': json.dumps(history_data_all)  # Pour la modal d'historique
        }
        return render(request, "chatbot.html", context)
    except Utilisateur.DoesNotExist:
        messages.error(request, "Session invalide. Veuillez vous reconnecter.")
        return redirect('/')