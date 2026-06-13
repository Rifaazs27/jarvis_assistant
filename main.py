import ollama
import datetime
import webbrowser
import pyttsx3
import speech_recognition as sr
import re
import os
import requests
from colorama import init, Fore, Style
from notion_client import Client

init(autoreset=True)

# --- CONFIGURATION NOTION ---
notion = Client(auth="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")
PAGE_ID = "37eddba847a88077a8f9d523621ca6bd"

# --- L'ANNUAIRE DES APPLICATIONS ---
APPLICATIONS_LOCALES = {
    "chrome": "chrome",
    "brave": "brave",
    "bloc-notes": "notepad",
    "calculatrice": "calc",
    "explorateur": "explorer"
}

def parler(texte):
    try:
        moteur = pyttsx3.init()
        moteur.setProperty('rate', 170)
        texte_propre = re.sub(r'\[.*?\]', '', texte).strip()
        texte_propre = re.sub(r'(OUVRIR|LANCER|CREER|SUPPRIMER|LIRE|NOTION|TERMINER).*', '', texte_propre, flags=re.IGNORECASE).strip()
        if texte_propre:
            moteur.say(texte_propre)
            moteur.runAndWait()
    except Exception as e:
        print(Fore.RED + f"[Erreur vocale : {e}]")

# --- LECTURE DU PLANNING NOTION ---
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
            date_prop = page['properties'].get("Date d’échéance", {}) or page['properties'].get("Date d'échéance", {})
            
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
        return f"Impossible de charger le planning. Erreur : {e}"

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
        reponse = requests.get(url, timeout=3)
        return reponse.text.strip()
    except:
        return "Météo indisponible"

# --- LE CERVEAU ---
historique_conversation = [
    {
        'role': 'system', 
        'content': (
            "Tu es Système, l'assistant IA exécutif de mon ordinateur. Tu es strict, froid et direct.\n"
            "RÈGLES ABSOLUES (Tu dois répondre par UNE SEULE ligne, AUCUN commentaire supplémentaire) :\n"
            "1. Discussion (heure, météo, questions) : Réponds naturellement sans balise.\n"
            "2. Lancer un logiciel (ex: Chrome) : [LANCER: nom].\n"
            "3. Ouvrir un site web : [OUVRIR: url_complete].\n"
            "4. Créer un FICHIER TEXTE sur l'ordinateur : [CREER: nom_fichier.ext | contenu].\n"
            "5. Supprimer un fichier : [SUPPRIMER: nom_fichier.ext].\n"
            "6. Verrouiller le PC : [VERROUILLER]. Éteindre : [ETEINDRE].\n"
            "7. Ajouter/Planifier une TÂCHE NOTION (planning) : [NOTION: nom_tache | AAAA-MM-JJ]. Convertis la date en AAAA-MM-JJ. Si aucune date n'est précisée, utilise la date du jour.\n"
            "8. Lire le planning Notion : [LIRE_NOTION].\n"
            "9. Terminer une tâche Notion : [TERMINER_NOTION: mot_cle_unique].\n"
            "INTERDICTION ABSOLUE : N'ajoute JAMAIS de commentaires ou de parenthèses comme '(A noter que...)'. Ne confonds pas TÂCHE (Notion) et FICHIER (Creer)."
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
    print(Fore.CYAN + Style.BRIGHT + " ⚡ SYSTÈME v4.0 - Intégration Notion Premium")
    print(Fore.CYAN + Style.BRIGHT + "========================================================")
    
    parler("Système en ligne. Synchronisation générale effectuée.")
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
                print(Fore.CYAN + f"Système : {message_fin}")
                parler(message_fin)
                break
            
            reponse_ia = demander_au_systeme(requete)
            
            # --- ACTIONS INDESTRUCTIBLES ---
            if re.search(r'LIRE_NOTION', reponse_ia, re.IGNORECASE):
                msg_notion = lire_notion()
                print(Fore.CYAN + f"Système : Analyse du planning.")
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
                    print(Fore.CYAN + f"Système : {msg}")
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
                    print(Fore.CYAN + f"Système : {msg}")
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
                    print(Fore.CYAN + f"Système : {msg}")
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
                    print(Fore.CYAN + f"Système : {msg}")
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
                    print(Fore.CYAN + f"Système : {msg}")
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
                    print(Fore.CYAN + f"Système : {msg}")
                    parler(msg)
                except Exception as e:
                    print(Fore.RED + f"Erreur suppression : {e}")

            elif re.search(r'VERROUILLER', reponse_ia, re.IGNORECASE):
                print(Fore.RED + "Système : Verrouillage...")
                parler("Verrouillage de la session.")
                os.system("rundll32.exe user32.dll,LockWorkStation")
                
            elif re.search(r'ETEINDRE', reponse_ia, re.IGNORECASE):
                print(Fore.RED + "Système : Extinction...")
                parler("Extinction dans une minute.")
                os.system("shutdown /s /t 60")
                
            else:
                print(Fore.CYAN + f"Système : {reponse_ia}")
                parler(reponse_ia)