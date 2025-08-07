import json
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.conf import settings
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import google.generativeai as genai
from .models import ChatBot, Utilisateur, UserFile
from PIL import Image
import mimetypes

# Import pour la lecture des différents types de fichiers
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("[WARNING] PyPDF2 non installé. Les fichiers PDF ne pourront pas être lus.")

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    print("[WARNING] python-docx non installé. Les fichiers Word ne pourront pas être lus.")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("[WARNING] pandas non installé. Les fichiers Excel/CSV ne pourront pas être lus.")

def connexion(request):
    if request.method == 'POST':
        nom = request.POST.get('username')
        password = request.POST.get('password1')

        try:
            user = Utilisateur.objects.get(nom=nom)
            if check_password(password, user.password):
                request.session['user_id'] = str(user.id)
                request.session['username'] = user.nom
                return redirect('/chatbot/')
            else:
                messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
                return redirect('/')
        except Utilisateur.DoesNotExist:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
            return redirect('/')
        except Exception as e:
            print(f"[ERREUR connexion] : {str(e)}")
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

        if password != confirmpassword:
            messages.error(request, "Les mots de passe ne correspondent pas.")
            return redirect('inscription')

        Utilisateur.objects.create(nom=nom, password=make_password(password))
        messages.success(request, "Inscription réussie. Vous pouvez maintenant vous connecter.")
        return redirect('connexion')

    return render(request, 'inscription.html')

def is_forbidden_topic(text):
    forbidden_keywords = [
        "religion", "dieu", "allah", "islam", "chrétien", "juif", "musulman",
        "sexe", "sexualité", "pornographie", "porno", "sexy", "seins", "sexe oral",
        "alcool", "alcoolisme", "ivresse",
        "meurtre", "assassinat", "tuer", "homicide",
        "insulte", "pute", "connard", "merde", "salope", "enculé", "bite", "couille",
        "fuck", "shit", "bitch", "asshole", "dick", "pussy"
    ]
    text_lower = text.lower()
    for keyword in forbidden_keywords:
        if keyword in text_lower:
            return True
    return False

def is_greeting(text):
    greeting_keywords = [
       'bonjour', 'salut', 'coucou', 'bonsoir', 'hello', 'hi', 'hey', 'salutations',
        'bonne journée', 'bonne soirée', 'yo', 'greetings', 'good morning', 'good evening', 'good afternoon',
        'how are you', 'ça va', 'comment ça va', 'bienvenue'
    ]
    text_lower = text.lower()
    
    # Vérifier si c'est une vraie salutation (pas une question sur un fichier)
    for keyword in greeting_keywords:
        if keyword in text_lower:
            # Si le texte contient des mots liés aux fichiers, ce n'est pas une salutation
            file_related_words = ['fichier', 'document', 'image', 'pdf', 'txt', 'doc', 'analyse', 'contenu', 'dit', 'contient']
            for file_word in file_related_words:
                if file_word in text_lower:
                    return False
            return True
    return False

def is_audit_related(text):
    audit_keywords = [
        "audit", "contrôle", "conformité", "risque", "audit interne", "audit externe",
        "audit financier", "audit qualité", "audit de conformité", "audit opérationnel",
        "audit des systèmes", "audit des processus", "audit des comptes", "audit légal",
        "audit réglementaire", "audit de gestion", "audit informatique", "compliance",
        "normes", "réglementation", "contrôle interne", "gestion des risques","procédures",
        "processus", "évaluation des risques", "analyse des risques", "audit de performance",
        "audit de sécurité", "audit environnemental", "audit social", "audit de projet", "audit de données",
        "audit de système d'information", "audit de la chaîne d'approvisionnement", "audit de la qualité",
        "audit de la gouvernance", "audit de la stratégie", "audit de la conformité réglementaire", "audit de la performance financière",
        "audit de la performance opérationnelle", "audit de la performance organisationnelle", "audit de la performance des processus",
        "audit de la performance des systèmes", "audit de la performance des projets", "audit de la performance des données", "audit de la performance des ressources humaines",
        "audit de la performance des technologies de l'information", "audit de la performance des infrastructures", "audit de la performance des services", "audit de la performance des produits",
        "audit de la performance des opérations", "audit de la performance des ventes", "audit de la performance du marketing", "audit de la performance de la chaîne logistique", "audit de la performance des finances",
        "audit de la performance de la gouvernance", "audit de la performance de la stratégie", "audit de la performance de la conformité",
        "audit de la performance de la sécurité", "audit de la performance environnementale", "audit de la performance sociale", "audit de la performance des ressources", "audit de la performance des processus métiers",
        "audit de la performance des systèmes d'information", "audit de la performance des technologies", "audit de la performance des infrastructures informatiques", "audit de la performance des services informatiques", "audit de la performance des produits informatiques",
        "audit de la performance des opérations informatiques", "audit de la performance des ventes informatiques", "audit de la performance du marketing informatique",
        "audit de la performance de la chaîne logistique informatique", "audit de la performance des finances informatiques",
        "audit de la performance de la gouvernance informatique", "audit de la performance de la stratégie informatique", "audit de la performance de la conformité informatique", "audit de la performance de la sécurité informatique",
        "audit de la performance environnementale informatique", "audit de la performance sociale informatique",
        # Mots-clés pour l'analyse de fichiers et documents
        "analyse", "analyser", "examiner", "examen", "vérifier", "vérification", "inspecter", "inspection",
        "évaluer", "évaluation", "revoir", "révision", "contrôler", "contrôle", "document", "rapport",
        "fichier", "dossier", "contenu", "information", "données", "résultats", "conclusions", "recommandations"
    ]
    text_lower = text.lower()
    for keyword in audit_keywords:
        if keyword in text_lower:
            return True
    return False

def ask_question(request):
    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée"}, status=405)

    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({"error": "Session expirée. Veuillez vous reconnecter."}, status=401)

    try:
        data = json.loads(request.body.decode("utf-8"))
        text = data.get("text", "").strip()
        file_id = data.get("file_id")
        file_name = data.get("file_name", "")
        
        print(f"[DEBUG] Données reçues - text: '{text}', file_id: {file_id}, file_name: '{file_name}'")
        
        if not text:
            return JsonResponse({"error": "Le message est vide."}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Format de données invalide."}, status=400)

    if is_forbidden_topic(text):
        refusal_message = "Je suis désolé, mais je ne peux pas répondre à cette question car elle concerne un sujet interdit en mon domaine d'expertise."
        return JsonResponse({"response": refusal_message})

    # PRIORITÉ 1: Vérifier les salutations (pour tous les cas)
    if is_greeting(text):
        greeting_response = "Bonjour , votre chatbot est prêt à vous aider ! Qu'est-ce que je peux faire pour vous ?"
        return JsonResponse({"response": greeting_response})
    
    # PRIORITÉ 2: Vérifier que la question est liée à l'audit (TOUJOURS requis)
    if not is_audit_related(text):
        refusal_message = "Je suis désolé, je ne peux répondre qu'aux questions liées à l'audit. Veuillez reformuler votre question."
        return JsonResponse({"response": refusal_message})

    try:
        user = Utilisateur.objects.get(id=user_id)
        recent_conversations = ChatBot.objects.filter(user=user).order_by('-created_at')[:5]

        # Préparer le prompt de base
        if file_id:
            prompt = "Vous êtes un assistant IA spécialisé en audit et analyse de documents. Répondez de manière professionnelle et précise.\n\n"
        else:
            prompt = "Vous êtes un chatbot spécialisé en audit. Répondez de manière professionnelle et précise.\n\n"

        # Ajouter l'historique des conversations
        prompt += "Voici l'historique des conversations précédentes pour le contexte :\n\n"
        for conv in reversed(recent_conversations):
            prompt += f"Question précédente : {conv.text_input}\n"
            prompt += f"Réponse précédente : {conv.gemini_output}\n\n"

        # Si un fichier est associé, analyser son contenu
        file_content = ""
        user_file = None
        if file_id:
            try:
                user_file = UserFile.objects.get(id=file_id, user=user)
                file_path = user_file.file.path
                
                # Lire le contenu du fichier selon son type
                if user_file.is_image():
                    # Pour les images, on peut utiliser Gemini Vision
                    file_content = f"L'utilisateur a uploadé une image nommée '{file_name}'. "
                    file_content += "Analysez cette image et répondez à la question en vous basant sur son contenu visuel."
                    # Ajouter le contenu au prompt pour les images aussi
                    prompt += f"CONTENU DU FICHIER '{file_name}' :\n{file_content}\n\n"
                else:
                    # Utiliser la nouvelle fonction pour lire tous types de fichiers
                    file_content = read_file_content(file_path, file_name)
                    
                    # Ajouter le contenu au prompt
                    prompt += f"CONTENU DU FICHIER '{file_name}' :\n{file_content}\n\n"
                
                # Debug temporaire pour voir le contenu
                print(f"[DEBUG CONTENU FICHIER] :\n{file_content}\n")
            except UserFile.DoesNotExist:
                return JsonResponse({"error": "Fichier non trouvé."}, status=404)
            except Exception as e:
                print(f"[ERREUR Lecture fichier] : {str(e)}")
                file_content = f"Erreur lors de la lecture du fichier '{file_name}'."

        prompt += f"Nouvelle question : {text}\n\n"
        
        # Debug du prompt final
        print(f"[DEBUG PROMPT FINAL] :\n{prompt}\n")
        
        if file_id:
            prompt += "Instructions :\n"
            prompt += "1. Analysez le contenu du fichier fourni dans une perspective d'audit et de contrôle.\n"
            prompt += "2. Identifiez les points de conformité, les risques, les procédures et les processus mentionnés.\n"
            prompt += "3. Répondez à la question en vous basant sur le contenu du fichier avec une approche d'auditeur.\n"
            prompt += "4. Si la question ne peut pas être répondue avec le contenu du fichier, indiquez-le clairement.\n"
            prompt += "5. Soyez professionnel, clair et précis dans votre analyse d'audit.\n"
            prompt += "6. Si la question n'est pas claire, demandez des précisions.\n"
            prompt += "7. Répondez toujours en français.\n"
        else:
            prompt += "Instructions :\n"
            prompt += "1. Répondez uniquement aux questions liées à l'audit ou proches de ce domaine.\n"
            prompt += "2. Soyez professionnel, clair et précis.\n"
            prompt += "3. Si la question n'est pas claire, demandez des précisions.\n"
            prompt += "4. Répondez toujours en français.\n"

        api_key = settings.GEMINI_API_KEY
        if not api_key:
            return JsonResponse({"error": "Clé API manquante."}, status=500)

        genai.configure(api_key=api_key)
        
        # Si c'est une image, utiliser Gemini Vision
        if file_id and user_file and user_file.is_image():
            try:
                model = genai.GenerativeModel("gemini-1.5-flash")
                image = Image.open(file_path)
                response = model.generate_content([prompt, image])
            except Exception as e:
                print(f"[ERREUR Gemini Vision] : {str(e)}")
                return JsonResponse({"error": "Erreur lors de l'analyse de l'image."}, status=500)
        else:
            # Pour le texte normal
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)

        ChatBot.objects.create(
            text_input=text,
            gemini_output=response.text,
            user=user
        )

        return JsonResponse({"response": response.text})

    except Exception as e:
        print(f"[ERREUR Gemini API] : {str(e)}")
        return JsonResponse({"error": "Erreur interne. Veuillez réessayer."}, status=500)

def chatbot_page(request):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, "Veuillez vous connecter pour accéder au chatbot.")
        return redirect('/')

    try:
        user = Utilisateur.objects.get(id=user_id)
        chat_history_all = ChatBot.objects.filter(user=user).order_by('-created_at')

        history_data_all = [
            {
                'message': chat.text_input,
                'response': chat.gemini_output,
                'timestamp': chat.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
            for chat in chat_history_all
        ]

        context = {
            'username': user.nom,
            'chat_history': json.dumps([]),
            'chat_history_all': json.dumps(history_data_all)
        }
        return render(request, "chatbot.html", context)
    except Utilisateur.DoesNotExist:
        messages.error(request, "Session invalide. Veuillez vous reconnecter.")
        return redirect('/')
    except Exception as e:
        print(f"[ERREUR Chatbot Page] : {str(e)}")
        messages.error(request, "Une erreur est survenue. Veuillez réessayer.")
        return redirect('/')

def upload_file(request):
    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée"}, status=405)
    
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({"error": "Session expirée. Veuillez vous reconnecter."}, status=401)
    
    try:
        user = Utilisateur.objects.get(id=user_id)
        
        if 'file' not in request.FILES:
            return JsonResponse({"error": "Aucun fichier fourni"}, status=400)
        
        uploaded_file = request.FILES['file']
        description = request.POST.get('description', '')
        
        # Vérifier la taille du fichier (max 10MB)
        if uploaded_file.size > 10 * 1024 * 1024:
            return JsonResponse({"error": "Le fichier est trop volumineux. Taille maximale : 10MB"}, status=400)
        
        # Déterminer le type de fichier
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
        file_type = 'other'
        
        if file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']:
            file_type = 'image'
        elif file_extension in ['.pdf', '.doc', '.docx', '.txt', '.rtf']:
            file_type = 'document'
        elif file_extension in ['.xls', '.xlsx', '.csv']:
            file_type = 'spreadsheet'
        elif file_extension in ['.ppt', '.pptx']:
            file_type = 'presentation'
        
        # Créer l'objet UserFile
        user_file = UserFile.objects.create(
            user=user,
            file=uploaded_file,
            file_name=uploaded_file.name,
            file_type=file_type,
            file_size=uploaded_file.size,
            description=description
        )
        
        return JsonResponse({
            "success": True,
            "file_id": user_file.id,
            "file_name": user_file.file_name,
            "file_type": user_file.file_type,
            "file_size_mb": user_file.get_file_size_mb(),
            "is_image": user_file.is_image(),
            "uploaded_at": user_file.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Utilisateur.DoesNotExist:
        return JsonResponse({"error": "Utilisateur non trouvé"}, status=404)
    except Exception as e:
        print(f"[ERREUR Upload] : {str(e)}")
        return JsonResponse({"error": "Erreur lors de l'upload du fichier"}, status=500)

def get_user_files(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({"error": "Session expirée. Veuillez vous reconnecter."}, status=401)
    
    try:
        user = Utilisateur.objects.get(id=user_id)
        files = UserFile.objects.filter(user=user)
        
        files_data = []
        for file in files:
            files_data.append({
                "id": file.id,
                "file_name": file.file_name,
                "file_type": file.file_type,
                "file_size_mb": file.get_file_size_mb(),
                "is_image": file.is_image(),
                "description": file.description,
                "uploaded_at": file.uploaded_at.strftime('%Y-%m-%d %H:%M:%S'),
                "url": file.file.url if file.file else None
            })
        
        return JsonResponse({"files": files_data})
        
    except Utilisateur.DoesNotExist:
        return JsonResponse({"error": "Utilisateur non trouvé"}, status=404)
    except Exception as e:
        print(f"[ERREUR Get Files] : {str(e)}")
        return JsonResponse({"error": "Erreur lors de la récupération des fichiers"}, status=500)

def download_file(request, file_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({"error": "Session expirée. Veuillez vous reconnecter."}, status=401)
    
    try:
        user = Utilisateur.objects.get(id=user_id)
        user_file = get_object_or_404(UserFile, id=file_id, user=user)
        
        if user_file.file and default_storage.exists(user_file.file.name):
            response = FileResponse(user_file.file, as_attachment=True, filename=user_file.file_name)
            return response
        else:
            return JsonResponse({"error": "Fichier non trouvé"}, status=404)
            
    except Utilisateur.DoesNotExist:
        return JsonResponse({"error": "Utilisateur non trouvé"}, status=404)
    except Exception as e:
        print(f"[ERREUR Download] : {str(e)}")
        return JsonResponse({"error": "Erreur lors du téléchargement"}, status=500)

def delete_file(request, file_id):
    if request.method != "DELETE":
        return JsonResponse({"error": "Méthode non autorisée"}, status=405)
    
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({"error": "Session expirée. Veuillez vous reconnecter."}, status=401)
    
    try:
        user = Utilisateur.objects.get(id=user_id)
        user_file = get_object_or_404(UserFile, id=file_id, user=user)
        
        # Supprimer le fichier physique
        if user_file.file and default_storage.exists(user_file.file.name):
            default_storage.delete(user_file.file.name)
        
        # Supprimer l'enregistrement de la base de données
        user_file.delete()
        
        return JsonResponse({"success": True, "message": "Fichier supprimé avec succès"})
        
    except Utilisateur.DoesNotExist:
        return JsonResponse({"error": "Utilisateur non trouvé"}, status=404)
    except Exception as e:
        print(f"[ERREUR Delete] : {str(e)}")
        return JsonResponse({"error": "Erreur lors de la suppression"}, status=500)

def get_file_preview(request, file_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({"error": "Session expirée. Veuillez vous reconnecter."}, status=401)
    
    try:
        user = Utilisateur.objects.get(id=user_id)
        user_file = get_object_or_404(UserFile, id=file_id, user=user)
        
        if not user_file.is_image():
            return JsonResponse({"error": "Aperçu disponible uniquement pour les images"}, status=400)
        
        if user_file.file and default_storage.exists(user_file.file.name):
            return JsonResponse({
                "success": True,
                "image_url": user_file.file.url,
                "file_name": user_file.file_name,
                "file_size_mb": user_file.get_file_size_mb(),
                "uploaded_at": user_file.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        else:
            return JsonResponse({"error": "Fichier non trouvé"}, status=404)
            
    except Utilisateur.DoesNotExist:
        return JsonResponse({"error": "Utilisateur non trouvé"}, status=404)
    except Exception as e:
        print(f"[ERREUR Preview] : {str(e)}")
        return JsonResponse({"error": "Erreur lors de l'aperçu"}, status=500)

def read_file_content(file_path, file_name):
    """
    Lit le contenu d'un fichier selon son type
    """
    file_extension = os.path.splitext(file_name)[1].lower()
    
    try:
        # Fichiers texte simples
        if file_extension in ['.txt', '.csv', '.json', '.xml', '.html', '.htm', '.md', '.log']:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except UnicodeDecodeError:
                try:
                    with open(file_path, 'r', encoding='latin-1') as f:
                        return f.read()
                except:
                    return f"Fichier '{file_name}' uploadé mais impossible de lire son contenu textuel."
        
        # Fichiers PDF
        elif file_extension == '.pdf' and PDF_AVAILABLE:
            try:
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    content = ""
                    for page_num, page in enumerate(reader.pages, 1):
                        page_text = page.extract_text()
                        if page_text:
                            content += f"\n--- Page {page_num} ---\n{page_text}\n"
                    return content if content else "Fichier PDF lu mais aucun texte extrait."
            except Exception as e:
                return f"Erreur lors de la lecture du PDF '{file_name}': {str(e)}"
        
        # Fichiers Word (.docx)
        elif file_extension == '.docx' and DOCX_AVAILABLE:
            try:
                doc = Document(file_path)
                content = ""
                for paragraph in doc.paragraphs:
                    if paragraph.text.strip():
                        content += paragraph.text + "\n"
                return content if content else "Fichier Word lu mais aucun texte extrait."
            except Exception as e:
                return f"Erreur lors de la lecture du fichier Word '{file_name}': {str(e)}"
        
        # Fichiers Excel (.xlsx, .xls)
        elif file_extension in ['.xlsx', '.xls'] and PANDAS_AVAILABLE:
            try:
                df = pd.read_excel(file_path)
                return f"Fichier Excel '{file_name}' - {len(df)} lignes, {len(df.columns)} colonnes\n\nContenu:\n{df.to_string()}"
            except Exception as e:
                return f"Erreur lors de la lecture du fichier Excel '{file_name}': {str(e)}"
        
        # Fichiers CSV
        elif file_extension == '.csv' and PANDAS_AVAILABLE:
            try:
                df = pd.read_csv(file_path)
                return f"Fichier CSV '{file_name}' - {len(df)} lignes, {len(df.columns)} colonnes\n\nContenu:\n{df.to_string()}"
            except Exception as e:
                return f"Erreur lors de la lecture du fichier CSV '{file_name}': {str(e)}"
        
        # Autres types de fichiers
        else:
            return f"Type de fichier '{file_extension}' non supporté pour la lecture. Veuillez utiliser un fichier texte, PDF, Word, Excel ou CSV."
            
    except Exception as e:
        return f"Erreur lors de la lecture du fichier '{file_name}': {str(e)}"