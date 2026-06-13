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

# --- LE CERVEAU ---
historique_conversation = [
    {
        'role': 'system', 
        'content': (
            "Tu es Système, l'assistant IA de mon ordinateur. "
            "RÈGLES STRICTES :\n"
            "1. Conversation normale : réponds en texte brut, SANS BALISE.\n"
            "2. Ouvrir un site : [OUVRIR: url].\n"
            "3. Lancer un logiciel : [LANCER: nom].\n"
            "4. Créer un fichier : [CREER: nom_fichier.ext | contenu].\n"
            "5. Verrouiller le PC : [VERROUILLER].\n"
            "6. Éteindre le PC : [ETEINDRE].\n"
            "7. Lire/Résumer un fichier : réponds [LIRE: nom_fichier.ext]. Utilise cette balise dès qu'on te demande 'dis-moi ce qu'il y a dans', 'lis', 'analyse' ou 'résume' un fichier.\n"
            "INTERDICTION ABSOLUE : N'invente JAMAIS d'autres balises."
        )
    }
]

def demander_au_systeme(texte_utilisateur):
    heure_actuelle = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    
    message_formate = (
        f"--- DONNÉES SYSTÈME ---\n"
        f"Heure: {heure_actuelle} | Météo: {obtenir_meteo()}\n"
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
    print(Fore.CYAN + Style.BRIGHT + " ⚡ SYSTÈME v2.9 - Recherche de Fichiers Floue Intelligente")
    print(Fore.CYAN + Style.BRIGHT + "========================================================")
    
    parler("Système en ligne. Moteur de recherche de fichiers optimisé.")
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
                    fin = reponse_ia.rfind("]") 
                    commande_creer = reponse_ia[debut:fin].strip()
                    
                    if "|" in commande_creer:
                        nom_fichier, contenu = commande_creer.split("|", 1)
                        nom_fichier = nom_fichier.strip()
                        contenu = contenu.strip()
                    else:
                        nom_fichier = commande_creer.strip()
                        contenu = "Fichier généré par Système IA."
                    
                    if "." not in nom_fichier: 
                        nom_fichier += ".txt"
                    
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

            # --- NOUVELLE ACTION AUTOMATISÉE : RECHERCHE INTÉLLIGENTE ---
            elif "[LIRE:" in reponse_ia:
                try:
                    debut = reponse_ia.find("[LIRE:") + 6
                    fin = reponse_ia.find("]", debut)
                    nom_fichier_ia = reponse_ia[debut:fin].strip()
                    
                    # Détection simplifiée du nom voulu par l'IA (ex: chaperon_rouge -> chaperonrouge)
                    nom_cible = os.path.splitext(nom_fichier_ia)[0].lower()
                    nom_cible = nom_cible.replace(" ", "").replace("_", "").replace("-", "")
                    
                    fichier_trouve = None
                    
                    # On scanne le bureau pour trouver le fichier correspondant
                    for f in os.listdir(chemin_bureau):
                        if os.path.isfile(os.path.join(chemin_bureau, f)):
                            nom_disque, ext_disque = os.path.splitext(f)
                            nom_disque_propre = nom_disque.lower().replace(" ", "").replace("_", "").replace("-", "")
                            
                            # Si les noms nettoyés matchent, on a trouvé notre cible !
                            if nom_disque_propre == nom_cible:
                                fichier_trouve = f
                                break
                    
                    if fichier_trouve:
                        chemin_complet = os.path.join(chemin_bureau, fichier_trouve)
                        with open(chemin_complet, 'r', encoding='utf-8') as f:
                            contenu_fichier = f.read()
                            
                        print(Fore.MAGENTA + f"Système : Analyse de {fichier_trouve}...")
                        
                        demande_lecture = f"Voici le contenu de {fichier_trouve} : '{contenu_fichier}'. Résume ou réponds naturellement à l'oral."
                        historique_conversation.append({'role': 'user', 'content': demande_lecture})
                        
                        reponse_lecture = ollama.chat(model='mistral', messages=historique_conversation)
                        texte_lu = reponse_lecture['message']['content']
                        
                        historique_conversation.append({'role': 'assistant', 'content': texte_lu})
                        
                        print(Fore.CYAN + f"Système : {texte_lu}")
                        parler(texte_lu)
                    else:
                        erreur = f"Désolé, je ne trouve aucun fichier ressemblant à '{nom_fichier_ia}' sur le bureau."
                        print(Fore.RED + f"Système : {erreur}")
                        parler(erreur)
                        
                except Exception as e:
                    print(Fore.RED + f"Erreur de lecture : {e}")
            
            # --- ACTIONS OS ---
            elif "[VERROUILLER]" in reponse_ia:
                print(Fore.RED + "Système : Verrouillage de la session en cours...")
                parler("Je verrouille votre session immédiatement.")
                os.system("rundll32.exe user32.dll,LockWorkStation")
                
            elif "[ETEINDRE]" in reponse_ia:
                print(Fore.RED + "Système : Extinction programmée dans 60 secondes.")
                parler("Attention. Le système s'éteindra dans une minute.")
                os.system("shutdown /s /t 60")
                
            else:
                print(Fore.CYAN + f"Système : {reponse_ia}")
                parler(reponse_ia)