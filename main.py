import ollama
import datetime
import webbrowser
import pyttsx3
import speech_recognition as sr
import re
import os
import requests
from colorama import init, Fore, Style

init(autoreset=True)

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
        if texte_propre:
            moteur.say(texte_propre)
            moteur.runAndWait()
    except Exception as e:
        print(Fore.RED + f"[Erreur vocale : {e}]")

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

# --- LE CERVEAU (LE STYLO DE L'IA) ---
historique_conversation = [
    {
        'role': 'system', 
        'content': (
            "Tu es Système, l'assistant IA de mon ordinateur. "
            "RÈGLES STRICTES :\n"
            "1. Météo/Heure : Utilise les DONNÉES SYSTÈME pour répondre naturellement.\n"
            "2. Ouvrir un site : réponds [OUVRIR: url].\n"
            "3. Lancer un logiciel : réponds [LANCER: nom].\n"
            "4. Créer un fichier : réponds [CREER: nom_fichier.ext | contenu exact]. "
            "Tu DOIS utiliser le symbole '|' pour séparer le nom du fichier et le contenu à écrire dedans. "
            "Rédige le code ou le texte demandé directement dans la section contenu.\n"
            "Exemple : Si l'utilisateur dit 'crée un script python qui dit bonjour', tu réponds UNIQUEMENT [CREER: bonjour.py | print('Bonjour')]."
        )
    }
]

def demander_au_systeme(texte_utilisateur):
    heure_actuelle = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    
    # On sépare visuellement les infos pour que l'IA ne les mélange plus avec ta commande
    message_formate = (
        f"--- DONNÉES SYSTÈME ---\n"
        f"Heure: {heure_actuelle} | Météo: {obtenir_meteo()}\n"
        f"--- COMMANDE UTILISATEUR ---\n"
        f"{texte_utilisateur}"
    )
    
    # On envoie le message formaté à l'IA
    historique_conversation.append({'role': 'user', 'content': message_formate})
    
    try:
        reponse = ollama.chat(model='mistral', messages=historique_conversation)
        texte_reponse = reponse['message']['content']
        
        # On nettoie l'historique
        historique_conversation[-1]['content'] = texte_utilisateur
        historique_conversation.append({'role': 'assistant', 'content': texte_reponse})
        
        return texte_reponse
    except Exception as e:
        historique_conversation.pop()
        return f"Erreur Ollama : {e}"

if __name__ == "__main__":
    print(Fore.CYAN + Style.BRIGHT + "========================================================")
    print(Fore.CYAN + Style.BRIGHT + " ⚡ SYSTÈME v2.6 - Le Stylo de l'IA (Création de contenu)")
    print(Fore.CYAN + Style.BRIGHT + "========================================================")
    
    parler("Système opérationnel. Mes modules de rédaction sont en ligne.")
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
            
            # --- ACTIONS ---
            if "[OUVRIR:" in reponse_ia:
                try:
                    url = re.search(r'\[OUVRIR: (.*?)\]', reponse_ia).group(1)
                    webbrowser.open_new_tab(url)
                    reponse_propre = reponse_ia[:reponse_ia.find("[OUVRIR:")].strip()
                    if reponse_propre:
                        print(Fore.CYAN + f"Système : {reponse_propre}")
                        parler(reponse_propre)
                except Exception as e:
                    print(Fore.RED + f"Erreur web : {e}")
                    
            elif "[LANCER:" in reponse_ia:
                try:
                    app = re.search(r'\[LANCER: (.*?)\]', reponse_ia).group(1).lower()
                    if app in APPLICATIONS_LOCALES: os.system(f"start {APPLICATIONS_LOCALES[app]}")
                    reponse_propre = reponse_ia[:reponse_ia.find("[LANCER:")].strip()
                    if reponse_propre:
                        print(Fore.CYAN + f"Système : {reponse_propre}")
                        parler(reponse_propre)
                except Exception as e:
                    print(Fore.RED + f"Erreur logiciel : {e}")
                    
            elif "[CREER:" in reponse_ia:
                try:
                    debut = reponse_ia.find("[CREER:") + 7
                    # rfind permet de chercher le tout dernier crochet de la réponse
                    fin = reponse_ia.rfind("]") 
                    commande_creer = reponse_ia[debut:fin].strip()
                    
                    # Découpage du nom et du contenu
                    if "|" in commande_creer:
                        nom_fichier, contenu = commande_creer.split("|", 1)
                        nom_fichier = nom_fichier.strip()
                        contenu = contenu.strip()
                    else:
                        nom_fichier = commande_creer.strip()
                        contenu = "Fichier généré par Système IA."
                    
                    # Sécurité : on ajoute .txt seulement s'il n'y a pas d'extension du tout (.py, .html, etc.)
                    if "." not in nom_fichier: 
                        nom_fichier += ".txt"
                    
                    # Création physique du fichier
                    with open(os.path.join(chemin_bureau, nom_fichier), 'w', encoding='utf-8') as f: 
                        f.write(contenu)
                    
                    reponse_propre = reponse_ia[:reponse_ia.find("[CREER:")].strip()
                    msg = f"J'ai créé le fichier {nom_fichier} avec le contenu demandé."
                    
                    if reponse_propre:
                        print(Fore.CYAN + f"Système : {reponse_propre}")
                        parler(reponse_propre)
                    else:
                        print(Fore.CYAN + f"Système : {msg}")
                        parler(msg)
                except Exception as e:
                    print(Fore.RED + f"Erreur création fichier : {e}")
                    
            else:
                print(Fore.CYAN + f"Système : {reponse_ia}")
                parler(reponse_ia)