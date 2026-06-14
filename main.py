import datetime
import webbrowser
import speech_recognition as sr
import re
import os
import requests
from colorama import init, Fore, Style
from notion_client import Client
import asyncio
import edge_tts
import tempfile
import pygame
from groq import Groq
from faster_whisper import WhisperModel
from dotenv import load_dotenv

load_dotenv()
init(autoreset=True)

# --- CONFIGURATIONS API ---
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PAGE_ID = os.getenv("PAGE_ID")

notion = Client(auth=NOTION_TOKEN)
client_groq = Groq(api_key=GROQ_API_KEY)

# --- L'ANNUAIRE DES APPLICATIONS ---
APPLICATIONS_LOCALES = {
    "chrome": "chrome.exe",
    "brave": "brave.exe",
    "discord": "discord.exe",
    "bloc-notes": "notepad.exe",
    "calculatrice": "calc.exe",
    "explorateur": "explorer.exe"
}

# --- CHARGEMENT DU MODÈLE VOCAL ---
print(Fore.CYAN + "[Initialisation du cortex auditif local (Whisper)...]")
modele_whisper = WhisperModel("base", device="cpu", compute_type="int8")

def parler(texte):
    try:
        texte_propre = re.sub(r'\[.*?\]', '', texte).strip()
        texte_propre = re.sub(r'[*#_]', '', texte_propre) 
        texte_propre = re.sub(r'(OUVRIR|LANCER|CREER|SUPPRIMER|LIRE|NOTION|TERMINER|RECHERCHER).*', '', texte_propre, flags=re.IGNORECASE).strip()
        
        if not texte_propre: return

        async def _synthese():
            # Correction ici : "Hz" au lieu de "%" pour le pitch
            communicate = edge_tts.Communicate(texte_propre, "fr-FR-HenriNeural", pitch="-15Hz", rate="-5%")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                chemin_tmp = f.name
            await communicate.save(chemin_tmp)
            return chemin_tmp

        chemin_audio = asyncio.run(_synthese())

        pygame.mixer.init()
        pygame.mixer.music.load(chemin_audio)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.quit()
        os.remove(chemin_audio)
    except Exception as e:
        print(Fore.RED + f"[Erreur vocale : {e}]")

def lire_notion():
    try:
        reponse = notion.databases.query(
            database_id=PAGE_ID,
            filter={"property": "État", "status": {"does_not_equal": "Terminé"}}
        )
        aujourdhui = datetime.datetime.now().strftime("%Y-%m-%d")
        taches_aujourdhui = []
        taches_futures = []
        
        for page in reponse.get('results', []):
            titre_prop = page['properties'].get('Nom de la tâche', {})
            date_prop = page['properties'].get("Date d’échéance", {}) or page['properties'].get("Date d'échéance", {})
            tache_texte = titre_prop['title'][0]['text']['content'] if titre_prop.get('title') else ""
            
            date_val = date_prop['date']['start'] if date_prop.get('date') and date_prop['date'] else ""
            
            if tache_texte:
                if date_val == aujourdhui:
                    taches_aujourdhui.append(tache_texte)
                else:
                    taches_futures.append(f"{tache_texte} (pour le {date_val})" if date_val else tache_texte)
        
        compte_rendu = ""
        if taches_aujourdhui:
            compte_rendu += "Pour aujourd'hui, vous avez : " + ", ".join(taches_aujourdhui) + ". "
        else:
            compte_rendu += "Vous n'avez aucune tâche de planifiée pour aujourd'hui. "
            
        if taches_futures:
            compte_rendu += "À venir prochainement : " + ", ".join(taches_futures) + "."
            
        return compte_rendu
    except Exception as e:
        return f"Impossible de charger le planning. Erreur : {e}"

recognizer = sr.Recognizer()

def ecouter(source, mode_silencieux=False):
    if not mode_silencieux:
        print(Fore.YELLOW + "\n[🔴 Jarvis écoute ta commande...]")
    try:
        # Écoute brève
        audio = recognizer.listen(source, timeout=5, phrase_time_limit=5 if mode_silencieux else 10)
        
        if mode_silencieux:
            # PETIT CERVEAU : On utilise Google juste pour guetter le mot "Jarvis" (hyper léger)
            texte = recognizer.recognize_google(audio, language="fr-FR").lower()
            return texte
        else:
            # GROS CERVEAU : Whisper prend le relais pour la vraie commande locale
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                f.write(audio.get_wav_data())
                chemin_audio_tmp = f.name
                
            segments, _ = modele_whisper.transcribe(chemin_audio_tmp, language="fr", beam_size=5)
            texte = " ".join([segment.text for segment in segments]).strip().lower()
            
            os.remove(chemin_audio_tmp) 
            texte = re.sub(r'[^\w\s]', '', texte) 
            
            if texte:
                print(Fore.GREEN + f"Toi : {texte}")
            return texte
            
    except Exception:
        return ""

def obtenir_meteo():
    try:
        url = "https://wttr.in/Garges-les-Gonesse?format=%C+%t"
        reponse = requests.get(url, timeout=3)
        return reponse.text.strip()
    except:
        return "Météo indisponible"

# --- LE CERVEAU ---
historique_conversation = [
    {
        'role': 'system', 
        'content': (
            "Tu es Jarvis, mon assistant IA personnel.\n"
            "RÈGLES ABSOLUES (Applique LA bonne règle selon ma commande. N'utilise qu'UNE SEULE balise) :\n"
            "1. Demande d'information/conseil (culture, jeux, comparatifs) : Donne une réponse orale détaillée ET ajoute à la fin la balise [RECHERCHER: mots_cles].\n"
            "2. Lancer un logiciel (ex: Chrome, Brave, Discord, Calculatrice...), même si j'utilise le mot 'Ouvre' : Phrase courte de confirmation ET [LANCER: nom_du_logiciel].\n"
            "3. Ouvrir un site web précis : Phrase courte ET [OUVRIR: url_complete].\n"
            "4. Créer un fichier : Phrase courte ET [CREER: nom_fichier.ext | contenu_optionnel].\n"
            "5. Supprimer un fichier : Phrase courte ET [SUPPRIMER: nom_fichier.ext].\n"
            "6. Verrouiller le PC : [VERROUILLER]. Éteindre : [ETEINDRE].\n"
            "7. Ajouter une tâche Notion : Phrase courte de confirmation ET [NOTION: nom_tache | AAAA-MM-JJ] (convertis la date).\n"
            "8. Lire le planning Notion : [LIRE_NOTION].\n"
            "9. Terminer une tâche Notion : Phrase courte ET [TERMINER_NOTION: mot_cle_unique].\n"
            "10. Discussion simple (heure, météo) : Réponds naturellement, SANS AUCUNE BALISE.\n"
            "INTERDICTION ABSOLUE : Ne mets JAMAIS la balise [RECHERCHER] si on te demande de lancer un logiciel, créer un fichier ou gérer Notion."
        )
    }
]

def demander_au_systeme(texte_utilisateur):
    heure_actuelle = datetime.datetime.now().strftime("%Hh%M")
    date_actuelle = datetime.datetime.now().strftime("%Y-%m-%d")
    
    message_formate = (
        f"--- DONNÉES SYSTÈME ---\n"
        f"Date courante: {date_actuelle} | Heure: {heure_actuelle} | Météo: {obtenir_meteo()}\n"
        f"--- COMMANDE UTILISATEUR ---\n"
        f"{texte_utilisateur}"
    )
    
    historique_conversation.append({'role': 'user', 'content': message_formate})
    
    try:
        reponse = client_groq.chat.completions.create(
            messages=historique_conversation,
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=800
        )
        texte_reponse = reponse.choices[0].message.content
        
        historique_conversation[-1]['content'] = texte_utilisateur
        historique_conversation.append({'role': 'assistant', 'content': texte_reponse})
        
        return texte_reponse
    except Exception as e:
        historique_conversation.pop()
        return f"Erreur Moteur IA : {e}"

if __name__ == "__main__":
    print(Fore.CYAN + Style.BRIGHT + "========================================================")
    print(Fore.CYAN + Style.BRIGHT + " ⚡ JARVIS v6.1 - Mot de Réveil & Accueil")
    print(Fore.CYAN + Style.BRIGHT + "========================================================")
    
    chemin_bureau = os.path.join(os.path.expanduser("~"), "Desktop")
    
    with sr.Microphone() as source:
        print(Fore.CYAN + "[Calibrage du bruit ambiant...]")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        
        # L'accueil au démarrage
        msg_notion = lire_notion()
        parler(f"Bonjour monsieur. {msg_notion} En quoi puis-je vous aider aujourd'hui ?")
        
        while True:
            print(Style.DIM + "\n[💤 Mode Veille : En attente du mot 'Jarvis'...]")
            
            # Petit cerveau : attend le mot clé
            texte_entendu = ecouter(source, mode_silencieux=True)
            
            if "jarvis" in texte_entendu:
                commande = texte_entendu.replace("jarvis", "").strip()
                if not commande:
                    parler("Oui monsieur ?")
                    # Gros cerveau (Whisper) : écoute la commande complexe
                    requete = ecouter(source, mode_silencieux=False)
                else:
                    requete = commande
                    print(Fore.GREEN + f"Toi : Jarvis, {requete}")

                if not requete: continue
                
                if requete in ['quitter', 'arrête-toi', 'désactiver', 'repos']: 
                    message_fin = "Extinction des programmes. À bientôt."
                    print(Fore.CYAN + f"Jarvis : {message_fin}")
                    parler(message_fin)
                    break
                
                reponse_ia = demander_au_systeme(requete)
                
                # --- ACTIONS INDESTRUCTIBLES ---
                if re.search(r'LIRE_NOTION', reponse_ia, re.IGNORECASE):
                    msg_notion = lire_notion()
                    print(Fore.CYAN + f"Jarvis : Analyse du planning.")
                    print(Fore.MAGENTA + msg_notion)
                    parler(f"Analyse du planning. {msg_notion}")

                elif re.search(r'TERMINER_NOTION\s*:', reponse_ia, re.IGNORECASE):
                    try:
                        tache_cible = re.search(r'TERMINER_NOTION\s*:\s*([^\]\n]+)', reponse_ia, re.IGNORECASE).group(1).lower().strip()
                        reponse_api = notion.databases.query(
                            database_id=PAGE_ID,
                            filter={"property": "État", "status": {"does_not_equal": "Terminé"}}
                        )
                        trouve = False
                        for page in reponse_api.get('results', []):
                            titre_prop = page['properties'].get('Nom de la tâche', {})
                            if titre_prop.get('title'):
                                texte_bloc = titre_prop['title'][0]['text']['content'].lower()
                                if tache_cible in texte_bloc:
                                    notion.pages.update(
                                        page_id=page['id'],
                                        properties={"État": {"status": {"name": "Terminé"}}}
                                    )
                                    trouve = True
                                    break
                        if trouve:
                            msg = f"La tâche contenant le mot {tache_cible} a été marquée comme terminée."
                        else:
                            msg = f"Je n'ai pas trouvé la tâche {tache_cible} dans votre liste."
                        print(Fore.CYAN + f"Jarvis : {msg}")
                        parler(msg)
                    except Exception as e:
                        print(Fore.RED + f"Erreur Notion terminaison : {e}")

                elif re.search(r'NOTION\s*:', reponse_ia, re.IGNORECASE):
                    try:
                        contenu_notion = re.search(r'NOTION\s*:\s*([^\]\n]+)', reponse_ia, re.IGNORECASE).group(1).strip()
                        date_tache = datetime.datetime.now().strftime("%Y-%m-%d")
                        tache = contenu_notion
                        
                        if "|" in contenu_notion:
                            tache, date_str = contenu_notion.split("|", 1)
                            tache = tache.strip()
                            date_tache = date_str.strip()
                        
                        colonne_date = "Date d’échéance"
                        
                        notion.pages.create(
                            parent={"database_id": PAGE_ID},
                            properties={
                                "Nom de la tâche": {"title": [{"text": {"content": tache}}]},
                                colonne_date: {"date": {"start": date_tache}}
                            }
                        )
                        msg = f"La tâche '{tache}' a bien été planifiée pour le {date_tache}."
                        print(Fore.CYAN + f"Jarvis : {msg}")
                        parler(msg)
                    except Exception as e:
                        print(Fore.RED + f"Erreur insertion Notion : {e}")

                elif re.search(r'OUVRIR\s*:', reponse_ia, re.IGNORECASE):
                    try:
                        cible = re.search(r'OUVRIR\s*:\s*([^\]\n]+)', reponse_ia, re.IGNORECASE).group(1).strip()
                        cible = cible.rstrip('.').lower()
                        if cible in APPLICATIONS_LOCALES:
                            os.system(f"start {APPLICATIONS_LOCALES[cible]}")
                        else:
                            if not cible.startswith("http"):
                                cible = "https://" + cible
                            webbrowser.open_new_tab(cible)
                        msg = f"Ouverture de {cible}."
                        print(Fore.CYAN + f"Jarvis : {msg}")
                        parler(msg)
                    except Exception as e:
                        print(Fore.RED + f"Erreur web : {e}")
                        
                elif re.search(r'LANCER\s*:', reponse_ia, re.IGNORECASE):
                    try:
                        app = re.search(r'LANCER\s*:\s*([^\]\n]+)', reponse_ia, re.IGNORECASE).group(1).strip()
                        app = app.rstrip('.').lower()
                        if app in APPLICATIONS_LOCALES: 
                            os.system(f"start {APPLICATIONS_LOCALES[app]}")
                        else:
                            os.system(f"start {app}")
                        msg = f"Lancement de {app}."
                        print(Fore.CYAN + f"Jarvis : {msg}")
                        parler(msg)
                    except Exception as e:
                        print(Fore.RED + f"Erreur logiciel : {e}")
                        
                elif re.search(r'CREER\s*:', reponse_ia, re.IGNORECASE):
                    try:
                        contenu_brut = re.search(r'CREER\s*:\s*([^\]\n]+)', reponse_ia, re.IGNORECASE).group(1).strip()
                        if "|" in contenu_brut:
                            nom_fichier, contenu = contenu_brut.split("|", 1)
                            nom_fichier = nom_fichier.strip()
                            contenu = contenu.strip()
                        else:
                            nom_fichier = contenu_brut.strip()
                            contenu = "Fichier généré par Système IA."
                        if "." not in nom_fichier: 
                            nom_fichier += ".txt"
                        with open(os.path.join(chemin_bureau, nom_fichier), 'w', encoding='utf-8') as f: 
                            f.write(contenu)
                        msg = f"J'ai créé le fichier {nom_fichier}."
                        print(Fore.CYAN + f"Jarvis : {msg}")
                        parler(msg)
                    except Exception as e:
                        print(Fore.RED + f"Erreur création fichier : {e}")

                elif re.search(r'SUPPRIMER\s*:', reponse_ia, re.IGNORECASE):
                    try:
                        nom_fichier = re.search(r'SUPPRIMER\s*:\s*([^\]\n]+)', reponse_ia, re.IGNORECASE).group(1).strip()
                        nom_fichier = nom_fichier.rstrip('.')
                        if "." not in nom_fichier:
                            nom_fichier += ".txt"
                        chemin_complet = os.path.join(chemin_bureau, nom_fichier)
                        if os.path.exists(chemin_complet):
                            os.remove(chemin_complet)
                            msg = f"Le fichier {nom_fichier} a été supprimé."
                        else:
                            msg = f"Je ne trouve pas {nom_fichier}."
                        print(Fore.CYAN + f"Jarvis : {msg}")
                        parler(msg)
                    except Exception as e:
                        print(Fore.RED + f"Erreur suppression : {e}")

                elif re.search(r'VERROUILLER', reponse_ia, re.IGNORECASE):
                    print(Fore.RED + "Jarvis : Verrouillage...")
                    parler("Verrouillage de la session.")
                    os.system("rundll32.exe user32.dll,LockWorkStation")
                    
                elif re.search(r'ETEINDRE', reponse_ia, re.IGNORECASE):
                    print(Fore.RED + "Jarvis : Extinction...")
                    parler("Extinction dans une minute.")
                    os.system("shutdown /s /t 60")
                    
                elif re.search(r'RECHERCHER\s*:', reponse_ia, re.IGNORECASE):
                    try:
                        requete_recherche = re.search(r'RECHERCHER\s*:\s*([^\]\n]+)', reponse_ia, re.IGNORECASE).group(1).strip()
                        requete_recherche = requete_recherche.rstrip('.')
                        
                        url_recherche = f"https://www.google.com/search?q={requests.utils.quote(requete_recherche)}"
                        webbrowser.open_new_tab(url_recherche)
                        
                        reponse_propre = re.sub(r'\[.*?\]', '', reponse_ia).strip()
                        reponse_propre = re.sub(r'[*#_]', '', reponse_propre)
                        msg = reponse_propre if reponse_propre else f"Recherche en cours pour {requete_recherche}."
                        
                        print(Fore.CYAN + f"Jarvis : {msg}")
                        parler(msg)
                    except Exception as e:
                        print(Fore.RED + f"Erreur de recherche : {e}")
                    
                else:
                    print(Fore.CYAN + f"Jarvis : {reponse_ia}")
                    parler(reponse_ia)