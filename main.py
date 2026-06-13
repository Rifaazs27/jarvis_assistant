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
            
        except sr.WaitTimeoutError:
            return ""
        except sr.UnknownValueError:
            if not mode_silencieux:
                print(Fore.CYAN + "\n[Système : Je n'ai pas bien compris la commande.]")
                parler("Je n'ai pas bien compris.")
            return ""
        except Exception as e:
            if not mode_silencieux:
                print(Fore.RED + f"\n[Erreur micro : {e}]")
            return ""

def obtenir_meteo():
    try:
        url = "https://wttr.in/Garges-les-Gonesse?format=%C+%t"
        reponse = requests.get(url, timeout=3)
        return reponse.text.strip()
    except:
        return "Météo indisponible"

# --- LA MÉMOIRE & LE CERVEAU ---
historique_conversation = [
    {
        'role': 'system', 
        'content': (
            "Tu es Système, l'assistant IA de mon ordinateur. Tu es direct et concis. "
            "VOICI TES 3 SEULS POUVOIRS (Tu dois utiliser ces balises exactes) : "
            "1. Pour ouvrir un site : [OUVRIR: url] "
            "2. Pour lancer un logiciel : [LANCER: nom_logiciel] "
            "3. Pour créer un fichier : [CREER: nom_fichier.ext] "
            "INTERDICTION ABSOLUE : N'invente JAMAIS d'autres balises (pas de [REPONSE:], pas de [FERMER:]). "
            "Si tu ne peux pas faire une action, dis-le simplement en texte normal."
        )
    }
]

def demander_au_systeme(texte_utilisateur):
    heure_actuelle = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    meteo_actuelle = obtenir_meteo()
    
    contexte_total = f"[Contexte -> Date/Heure: {heure_actuelle} | Météo: {meteo_actuelle}] "
    historique_conversation.append({'role': 'user', 'content': contexte_total + texte_utilisateur})
    
    try:
        reponse = ollama.chat(model='mistral', messages=historique_conversation)
        texte_reponse = reponse['message']['content']
        historique_conversation.append({'role': 'assistant', 'content': texte_reponse})
        return texte_reponse
    except Exception as e:
        historique_conversation.pop()
        return f"Erreur Ollama : {e}"

if __name__ == "__main__":
    print(Fore.CYAN + Style.BRIGHT + "========================================================")
    print(Fore.CYAN + Style.BRIGHT + " ⚡ SYSTÈME v2.1 - Contrôle Fichiers & Anti-Hallucinations")
    print(Fore.CYAN + Style.BRIGHT + "========================================================")
    
    parler("Mise à jour terminée. Je peux maintenant créer des fichiers sur votre bureau.")
    
    # On identifie le chemin du Bureau de ton Windows
    chemin_bureau = os.path.join(os.path.expanduser("~"), "Desktop")
    
    while True:
        print(Style.DIM + "\n[💤 Mode Veille : En attente du mot 'Système'...]")
        texte_entendu = ecouter(mode_silencieux=True)
        
        if "système" in texte_entendu or "systeme" in texte_entendu:
            commande = texte_entendu.replace("système", "").replace("systeme", "").strip()
            
            if commande:
                requete = commande
                print(Fore.GREEN + f"Toi : Système, {requete}")
            else:
                parler("Oui monsieur ?")
                requete = ecouter(mode_silencieux=False)
                if not requete:
                    continue
            
            if requete in ['exit', 'quit', 'quitter', 'désactiver', 'arrête-toi']:
                message_fin = "Extinction des programmes. À bientôt."
                print(Fore.CYAN + f"Système : {message_fin}")
                parler(message_fin)
                break
            
            reponse_ia = demander_au_systeme(requete)
            
            # --- ACTION 1 : NAVIGATION WEB ---
            if "[OUVRIR:" in reponse_ia:
                try:
                    debut = reponse_ia.find("[OUVRIR:") + 8
                    fin = reponse_ia.find("]", debut)
                    url = reponse_ia[debut:fin].strip()
                    webbrowser.open_new_tab(url)
                    reponse_propre = reponse_ia[:reponse_ia.find("[OUVRIR:")].strip()
                    if reponse_propre:
                        print(Fore.CYAN + f"Système : {reponse_propre}")
                        parler(reponse_propre)
                except Exception as e:
                    print(Fore.RED + f"Erreur web : {e}")
            
            # --- ACTION 2 : LANCEMENT DE LOGICIEL ---
            elif "[LANCER:" in reponse_ia:
                try:
                    debut = reponse_ia.find("[LANCER:") + 8
                    fin = reponse_ia.find("]", debut)
                    app_demande = reponse_ia[debut:fin].strip().lower()
                    if app_demande in APPLICATIONS_LOCALES:
                        os.system(f"start {APPLICATIONS_LOCALES[app_demande]}")
                    reponse_propre = reponse_ia[:reponse_ia.find("[LANCER:")].strip()
                    if reponse_propre:
                        print(Fore.CYAN + f"Système : {reponse_propre}")
                        parler(reponse_propre)
                except Exception as e:
                    print(Fore.RED + f"Erreur logiciel : {e}")
                    
            # --- ACTION 3 : CRÉATION DE FICHIER (NOUVEAU) ---
            elif "[CREER:" in reponse_ia:
                try:
                    debut = reponse_ia.find("[CREER:") + 7
                    fin = reponse_ia.find("]", debut)
                    nom_fichier = reponse_ia[debut:fin].strip()
                    
                    # On crée le chemin complet vers ton Bureau
                    chemin_complet = os.path.join(chemin_bureau, nom_fichier)
                    
                    # On crée le fichier
                    with open(chemin_complet, 'w', encoding='utf-8') as f:
                        f.write("Fichier généré par Système IA.")
                        
                    reponse_propre = reponse_ia[:reponse_ia.find("[CREER:")].strip()
                    msg_succes = f"J'ai créé le fichier {nom_fichier} sur votre bureau."
                    
                    if reponse_propre:
                        print(Fore.CYAN + f"Système : {reponse_propre} ({msg_succes})")
                        parler(reponse_propre)
                    else:
                        print(Fore.CYAN + f"Système : {msg_succes}")
                        parler(msg_succes)
                        
                except Exception as e:
                    erreur = "Je n'ai pas pu créer le fichier."
                    print(Fore.RED + f"Système : {erreur} ({e})")
                    parler(erreur)

            # --- ACTION 4 : DISCUSSION NORMALE ---
            else:
                print(Fore.CYAN + f"Système : {reponse_ia}")
                parler(reponse_ia)