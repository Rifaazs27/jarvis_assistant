import ollama
import datetime
import webbrowser
import speech_recognition as sr
import re
import os
import requests
import pyautogui
from colorama import init, Fore, Style
from notion_client import Client
import asyncio
import edge_tts
import tempfile
import pygame

notion = Client(auth="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")
PAGE_ID = "37eddba847a88077a8f9d523621ca6bd"

init(autoreset=True)

APPLICATIONS_LOCALES = {
    "chrome": "chrome.exe",
    "brave": "brave.exe",
    "bloc-notes": "notepad.exe",
    "calculatrice": "calc.exe",
    "explorateur": "explorer.exe"
}

def parler(texte):
    try:
        texte_propre = re.sub(r'\[.*?\]', '', texte).strip()
        texte_vocal = texte_propre.replace("/", " sur ").replace("*", "").replace("_", " ")
        if not texte_vocal:
            return

        async def _synthese():
            communicate = edge_tts.Communicate(texte_vocal, "fr-FR-HenriNeural", rate="+10%", volume="+0%")
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

# --- LECTURE INTELLIGENTE DU PLANNING ---
def lire_notion():
    try:
        reponse = notion.databases.query(
            database_id=PAGE_ID,
            filter={
                "property": "État",
                "status": {
                    "does_not_equal": "Terminé"
                }
            }
        )
        
        aujourdhui = datetime.datetime.now().strftime("%Y-%m-%d")
        taches_aujourdhui = []
        taches_futures = []
        
        for page in reponse.get('results', []):
            titre_prop = page['properties'].get('Nom de la tâche', {})
            date_prop = page['properties'].get("Date d\u2019\u00e9ch\u00e9ance", {}) or page['properties'].get("Date d'\u00e9ch\u00e9ance", {})
            
            tache_texte = ""
            if titre_prop.get('title'):
                tache_texte = titre_prop['title'][0]['text']['content']
            
            date_val = ""
            if date_prop.get('date') and date_prop['date']:
                date_val = date_prop['date']['start']
            
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
        return f"Je n'ai pas pu charger votre emploi du temps. Erreur : {e}"

recognizer = sr.Recognizer()

def ecouter(mode_silencieux=False):
    with sr.Microphone() as source:
        if not mode_silencieux:
            print(Fore.YELLOW + "\n[🔴 Système écoute ta commande...]")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            texte = recognizer.recognize_google(audio, language="fr-FR").lower()
            if not mode_silencieux:
                print(Fore.GREEN + f"Toi : {texte}")
            return texte
        except:
            return ""

def obtenir_meteo():
    try:
        url = "https://wttr.in/Garges-les-Gonesse?format=%C+%t"
        return requests.get(url, timeout=3).text.strip()
    except:
        return "Météo indisponible"

# --- LE CERVEAU ---
historique_conversation = [
    {
        'role': 'system', 
        'content': (
            "Tu es Système, l'assistant IA exécutif de mon ordinateur, inspiré de Jarvis. Tu n'es PAS un tutoriel.\n"
            "RÈGLES STRICTES :\n"
            "1. N'explique JAMAIS comment faire. Exécute directement avec la balise.\n"
            "2. Fais une seule phrase de confirmation naturelle, SUIVIE IMMÉDIATEMENT de la balise.\n"
            "3. Actions de base : [OUVRIR: url], [LANCER: nom], [FERMER: nom], [CREER: dossier/fichier|contenu], [LIRE: fichier], [MUTE], [VOL_PLUS], [VOL_MOINS], [CAPTURE], [VIDER_CORBEILLE], [VERROUILLER], [ETEINDRE], [DOSSIER: chemin], [RESTAURER: navigateur].\n"
            "4. Ajouter une tâche Notion : utilise le format [NOTION: nom_de_la_tache | AAAA-MM-JJ]. Calcule la date de l'échéance de manière très précise à l'aide de la date courante transmise dans les données système. Si l'utilisateur mentionne 'demain', 'lundi prochain' ou une date spécifique, convertis-la rigoureusement en AAAA-MM-JJ. Si aucune date/temporalité n'est détectée, utilise la date du jour actuel.\n"
            "5. Lire mon planning Notion : [LIRE_NOTION].\n"
            "6. Marquer une tâche comme terminée : [TERMINER_NOTION: UN_SEUL_MOT_CLE].\n"
            "INTERDICTION ABSOLUE : N'invente d'autres balises sous aucun prétexte."
        )
    }
]

def demander_au_systeme(texte_utilisateur):
    heure_actuelle = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    message_formate = f"--- DONNÉES SYSTÈME ---\nDate et Heure actuelles: {heure_actuelle} | Météo: {obtenir_meteo()}\n--- COMMANDE UTILISATEUR ---\n{texte_utilisateur}"
    historique_conversation.append({'role': 'user', 'content': message_formate})
    
    try:
        reponse = ollama.chat(model='mistral', messages=historique_conversation)
        texte_reponse = reponse['message']['content']
        historique_conversation[-1]['content'] = texte_utilisateur
        historique_conversation.append({'role': 'assistant', 'content': texte_reponse})
        return texte_reponse
    except Exception as e:
        historique_conversation.pop()
        return f"Erreur Ollama : {e}"

if __name__ == "__main__":
    print(Fore.CYAN + Style.BRIGHT + "========================================================")
    print(Fore.CYAN + Style.BRIGHT + " ⚡ SYSTÈME v4.8 - EMPLOI DU TEMPS DYNAMIQUE")
    print(Fore.CYAN + Style.BRIGHT + "========================================================")
    
    parler("Système en ligne. Synchronisation de votre emploi du temps.")
    briefing_matinal = lire_notion()
    print(Fore.CYAN + f"Système : {briefing_matinal}")
    parler(briefing_matinal)
    
    chemin_bureau = os.path.join(os.path.expanduser("~"), "Desktop")
    
    while True:
        print(Style.DIM + "\n[💤 Mode Veille : En attente du mot 'Système'...]")
        texte_entendu = ecouter(mode_silencieux=True)
        
        if "système" in texte_entendu or "systeme" in texte_entendu:
            commande = texte_entendu.replace("système", "").replace("systeme", "").strip()
            if not commande:
                parler("Oui monsieur ?")
                requete = ecouter(mode_silencieux=False)
            else:
                requete = commande
                print(Fore.GREEN + f"Toi : Système, {requete}")

            if not requete: continue
            
            if requete in ['quitter', 'arrête-toi', 'désactiver']: 
                message_fin = "Extinction des programmes. À bientôt."
                print(Fore.CYAN + f"Système : {message_fin}"); parler(message_fin)
                break
            
            reponse_ia = demander_au_systeme(requete)
            texte_naturel = re.sub(r'\[.*?\]', '', reponse_ia).strip()
            
            # --- ACTIONS NOTION EXTENSION DATATION ---
            if "[NOTION:" in reponse_ia:
                try:
                    contenu_notion = re.search(r'\[NOTION: (.*?)\]', reponse_ia).group(1)
                    date_tache = datetime.datetime.now().strftime("%Y-%m-%d")
                    tache = contenu_notion
                    
                    if "|" in contenu_notion:
                        tache, date_str = contenu_notion.split("|", 1)
                        tache = tache.strip()
                        date_tache = date_str.strip()
                    
                    # Détection du nom exact de la colonne date
                    colonne_date = "Date d\u2019\u00e9ch\u00e9ance"
                    
                    notion.pages.create(
                        parent={"database_id": PAGE_ID},
                        properties={
                            "Nom de la tâche": {
                                "title": [{"text": {"content": tache}}]
                            },
                            colonne_date: {
                                "date": {"start": date_tache}
                            }
                        }
                    )
                    msg = texte_naturel if texte_naturel else f"C'est planifié pour le {date_tache}."
                    print(Fore.CYAN + f"Système : {msg}"); parler(msg)
                except Exception as e:
                    print(Fore.RED + f"Erreur d'insertion temporelle Notion : {e}")
            
            elif "[TERMINER_NOTION:" in reponse_ia:
                try:
                    tache_cible = re.search(r'\[TERMINER_NOTION: (.*?)\]', reponse_ia).group(1).lower()
                    mots_cibles = tache_cible.replace("'", " ").split()
                    mots_importants = [mot for mot in mots_cibles if len(mot) > 3]
                    
                    reponse_api = notion.databases.query(
                        database_id=PAGE_ID,
                        filter={"property": "État", "status": {"does_not_equal": "Terminé"}}
                    )
                    
                    trouve = False
                    for page in reponse_api.get('results', []):
                        titre_prop = page['properties'].get('Nom de la tâche', {})
                        if titre_prop.get('title'):
                            texte_bloc = titre_prop['title'][0]['text']['content'].lower()
                            if tache_cible in texte_bloc or any(mot in texte_bloc for mot in mots_importants):
                                notion.pages.update(
                                    page_id=page['id'],
                                    properties={"État": {"status": {"name": "Terminé"}}}
                                )
                                trouve = True
                                break
                    
                    if trouve:
                        msg = texte_naturel if texte_naturel else "C'est coché monsieur."
                        print(Fore.CYAN + f"Système : {msg}"); parler(msg)
                    else:
                        msg = "Je n'ai pas trouvé cette tâche dans votre planning en cours."
                        print(Fore.RED + f"Système : {msg}"); parler(msg)
                except Exception as e:
                    print(Fore.RED + f"Erreur de mise à jour Notion : {e}")
                    
            elif "[LIRE_NOTION]" in reponse_ia:
                notion_data = lire_notion()
                msg = texte_naturel if texte_naturel else "Analyse de votre planning en cours."
                print(Fore.CYAN + f"Système : {msg}\n{notion_data}")
                parler(f"{msg}. {notion_data}")
            
            # --- ACTIONS LOGICIELS ET FICHIERS ---
            elif "[OUVRIR:" in reponse_ia:
                try:
                    url = re.search(r'\[OUVRIR: (.*?)\]', reponse_ia).group(1)
                    webbrowser.open_new_tab(url)
                    msg = texte_naturel if texte_naturel else "Ouverture demandée."
                    print(Fore.CYAN + f"Système : {msg}"); parler(msg)
                except Exception as e: print(Fore.RED + f"Erreur web : {e}")
                    
            elif "[LANCER:" in reponse_ia:
                try:
                    app = re.search(r'\[LANCER: (.*?)\]', reponse_ia).group(1).lower()
                    if app in APPLICATIONS_LOCALES: os.system(f"start {APPLICATIONS_LOCALES[app]}")
                    else: os.system(f"start {app}")
                    msg = texte_naturel if texte_naturel else f"Lancement effectué."
                    print(Fore.CYAN + f"Système : {msg}"); parler(msg)
                except Exception as e: print(Fore.RED + f"Erreur logiciel : {e}")

            elif "[FERMER:" in reponse_ia:
                try:
                    app = re.search(r'\[FERMER: (.*?)\]', reponse_ia).group(1).lower()
                    exe_name = APPLICATIONS_LOCALES.get(app, f"{app}.exe")
                    os.system(f"taskkill /F /IM {exe_name} /T")
                    msg = texte_naturel if texte_naturel else f"Fermeture effectuée."
                    print(Fore.CYAN + f"Système : {msg}"); parler(msg)
                except Exception as e: print(Fore.RED + f"Erreur fermeture : {e}")
                    
            elif "[CREER:" in reponse_ia:
                try:
                    debut = reponse_ia.find("[CREER:") + 7; fin = reponse_ia.rfind("]") 
                    commande_creer = reponse_ia[debut:fin].strip()
                    if "|" in commande_creer:
                        nom_fichier, contenu = commande_creer.split("|", 1)
                        nom_fichier, contenu = nom_fichier.strip(), contenu.strip()
                    else:
                        nom_fichier, contenu = commande_creer.strip(), "Fichier généré par Système."
                    
                    nom_de_base = os.path.basename(nom_fichier)
                    if "." not in nom_de_base: nom_fichier += ".txt"
                    
                    chemin_complet = os.path.join(chemin_bureau, nom_fichier)
                    dossier_parent = os.path.dirname(chemin_complet)
                    if dossier_parent: os.makedirs(dossier_parent, exist_ok=True)
                    with open(chemin_complet, 'w', encoding='utf-8') as f: f.write(contenu)
                    msg = texte_naturel if texte_naturel else f"Création terminée."
                    print(Fore.CYAN + f"Système : {msg}"); parler(msg)
                except Exception as e: print(Fore.RED + f"Erreur création : {e}")

            elif "[LIRE:" in reponse_ia:
                try:
                    debut = reponse_ia.find("[LIRE:") + 6; fin = reponse_ia.find("]", debut)
                    nom_fichier_ia = reponse_ia[debut:fin].strip()
                    nom_cible = os.path.splitext(nom_fichier_ia)[0].lower().replace(" ", "").replace("_", "").replace("-", "")
                    
                    fichier_trouve = None
                    for f in os.listdir(chemin_bureau):
                        if os.path.isfile(os.path.join(chemin_bureau, f)):
                            if os.path.splitext(f)[0].lower().replace(" ", "").replace("_", "").replace("-", "") == nom_cible:
                                fichier_trouve = f; break
                    
                    if fichier_trouve:
                        with open(os.path.join(chemin_bureau, fichier_trouve), 'r', encoding='utf-8') as f: contenu = f.read()
                        demande = f"Voici le texte exact extrait de {fichier_trouve} :\n'{contenu}'\nFais un résumé de CE TEXTE UNIQUEMENT. N'invente rien d'extérieur."
                        historique_conversation.append({'role': 'user', 'content': demande})
                        texte_lu = ollama.chat(model='mistral', messages=historique_conversation)['message']['content']
                        historique_conversation.append({'role': 'assistant', 'content': texte_lu})
                        print(Fore.CYAN + f"Système : {texte_lu}"); parler(texte_lu)
                    else:
                        print(Fore.RED + f"Système : Fichier introuvable."); parler("Fichier introuvable.")
                except Exception as e: print(Fore.RED + f"Erreur lecture : {e}")

            elif "[DOSSIER:" in reponse_ia:
                try:
                    debut = reponse_ia.find("[DOSSIER:") + 9; fin = reponse_ia.find("]", debut)
                    chemin_dossier = reponse_ia[debut:fin].strip()
                    os.makedirs(os.path.join(chemin_bureau, chemin_dossier), exist_ok=True)
                    msg = texte_naturel if texte_naturel else f"Dossier créé."
                    print(Fore.CYAN + f"Système : {msg}"); parler(msg)
                except Exception as e: print(Fore.RED + f"Erreur création dossier : {e}")

            elif "[RESTAURER:" in reponse_ia:
                try:
                    debut = reponse_ia.find("[RESTAURER:") + 11; fin = reponse_ia.find("]", debut)
                    navigateur = reponse_ia[debut:fin].strip().lower()
                    if navigateur in ["chrome", "brave"]:
                        exe_name = APPLICATIONS_LOCALES.get(navigateur, f"{navigateur}.exe")
                        os.system(f'start {exe_name} --restore-last-session')
                        msg = texte_naturel if texte_naturel else f"Restauration effectuée."
                        print(Fore.CYAN + f"Système : {msg}"); parler(msg)
                    else:
                        print(Fore.RED + f"Système : Support indisponible."); parler("Indisponible.")
                except Exception as e: print(Fore.RED + f"Erreur restauration : {e}")

            # --- ACTIONS MATÉRIEL & OS ---
            elif "[MUTE]" in reponse_ia:
                pyautogui.press("volumemute")
                msg = texte_naturel if texte_naturel else "Ajustement du volume."
                print(Fore.CYAN + f"Système : {msg}"); parler(msg)
            elif "[VOL_PLUS]" in reponse_ia:
                for _ in range(5): pyautogui.press("volumeup")
                msg = texte_naturel if texte_naturel else "Volume augmenté."
                print(Fore.CYAN + f"Système : {msg}"); parler(msg)
            elif "[VOL_MOINS]" in reponse_ia:
                for _ in range(5): pyautogui.press("volumedown")
                msg = texte_naturel if texte_naturel else "Volume diminué."
                print(Fore.CYAN + f"Système : {msg}"); parler(msg)
            elif "[CAPTURE]" in reponse_ia:
                nom_capture = f"capture_ecran_{datetime.datetime.now().strftime('%H%M%S')}.png"
                pyautogui.screenshot(os.path.join(chemin_bureau, nom_capture))
                msg = texte_naturel if texte_naturel else "Capture sauvegardée."
                print(Fore.CYAN + f"Système : {msg}"); parler(msg)
            elif "[VIDER_CORBEILLE]" in reponse_ia:
                os.system('powershell.exe -Command "Clear-RecycleBin -Force"')
                msg = texte_naturel if texte_naturel else "Nettoyage effectué."
                print(Fore.CYAN + f"Système : {msg}"); parler(msg)
            elif "[VERROUILLER]" in reponse_ia:
                os.system("rundll32.exe user32.dll,LockWorkStation")
                msg = texte_naturel if texte_naturel else "Session verrouillée."
                print(Fore.RED + f"Système : {msg}"); parler(msg)
            elif "[ETEINDRE]" in reponse_ia:
                os.system("shutdown /s /t 60")
                msg = texte_naturel if texte_naturel else "Arrêt programmé."
                print(Fore.RED + f"Système : {msg}"); parler(msg)
            else:
                print(Fore.CYAN + f"Système : {reponse_ia}")
                parler(reponse_ia)