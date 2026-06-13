import ollama
import datetime
import webbrowser
import pyttsx3
import speech_recognition as sr
import re

def parler(texte):
    try:
        moteur = pyttsx3.init()
        moteur.setProperty('rate', 170)
        texte_propre = re.sub(r'\[.*?\]', '', texte).strip()
        if texte_propre:
            moteur.say(texte_propre)
            moteur.runAndWait()
    except Exception as e:
        print(f"[Erreur vocale Windows : {e}]")

recognizer = sr.Recognizer()

def ecouter(mode_silencieux=False):
    with sr.Microphone() as source:
        if not mode_silencieux:
            print("\n[🔴 Système écoute ta commande...]")
            
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            texte = recognizer.recognize_google(audio, language="fr-FR").lower()
            
            if not mode_silencieux:
                print(f"Toi : {texte}")
            return texte
            
        except sr.WaitTimeoutError:
            return ""
        except sr.UnknownValueError:
            if not mode_silencieux:
                print("\n[Système : Je n'ai pas bien compris la commande.]")
                parler("Je n'ai pas bien compris.")
            return ""
        except Exception as e:
            if not mode_silencieux:
                print(f"\n[Erreur micro : {e}]")
            return ""

# --- LA MÉMOIRE & LE CERVEAU ---
historique_conversation = [
    {
        'role': 'system', 
        'content': (
            "Tu es Système, l'assistant IA de mon ordinateur. "
            "RÈGLE 1 : Si on te demande d'OUVRIR ou d'ALLER sur un site web, tu DOIS ajouter la balise [OUVRIR: url]. "
            "RÈGLE 2 : Tu es physiquement INCAPABLE de fermer des pages, des onglets ou des applications. "
            "RÈGLE 3 : Si on te demande de FERMER quelque chose, tu dois IMPÉRATIVEMENT répondre 'Désolé, je ne sais pas encore fermer de fenêtres' SANS utiliser aucune balise."
        )
    }
]

def demander_au_systeme(texte_utilisateur):
    heure_actuelle = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    contexte_temporel = f"[Système : Nous sommes le {heure_actuelle}] "
    
    historique_conversation.append({'role': 'user', 'content': contexte_temporel + texte_utilisateur})
    
    try:
        reponse = ollama.chat(model='mistral', messages=historique_conversation)
        texte_reponse = reponse['message']['content']
        historique_conversation.append({'role': 'assistant', 'content': texte_reponse})
        return texte_reponse
    except Exception as e:
        historique_conversation.pop()
        return f"Erreur critique Ollama : {e}"

# --- BOUCLE PRINCIPALE ---
if __name__ == "__main__":
    print("=====================================")
    print(" Système v1.6 - Mode Veille & Nouveau Nom")
    print("=====================================")
    
    parler("Mode veille activé. Appelez-moi Système si vous avez besoin de moi.")
    
    while True:
        print("\n[💤 Mode Veille : En attente du mot 'Système'...]")
        texte_entendu = ecouter(mode_silencieux=True)
        
        # On vérifie les deux orthographes possibles
        if "système" in texte_entendu or "systeme" in texte_entendu:
            
            # On nettoie le mot d'activation pour isoler la commande
            commande = texte_entendu.replace("système", "").replace("systeme", "").strip()
            
            # Cas 1 : "Système ouvre github"
            if commande:
                requete = commande
                print(f"Toi : Système, {requete}")
                
            # Cas 2 : Juste "Système"
            else:
                parler("Oui monsieur ?")
                requete = ecouter(mode_silencieux=False)
                
                if not requete:
                    continue
            
            # --- TRAITEMENT DE LA COMMANDE ---
            if requete in ['exit', 'quit', 'quitter', 'désactiver', 'arrête-toi']:
                message_fin = "Extinction des programmes. À bientôt."
                print(f"Système : {message_fin}")
                parler(message_fin)
                break
            
            reponse_ia = demander_au_systeme(requete)
            
            if "[OUVRIR:" in reponse_ia:
                try:
                    debut = reponse_ia.find("[OUVRIR:") + 8
                    fin = reponse_ia.find("]", debut)
                    url = reponse_ia[debut:fin].strip()
                    
                    webbrowser.open_new_tab(url)
                    
                    reponse_propre = reponse_ia[:reponse_ia.find("[OUVRIR:")].strip()
                    if reponse_propre:
                        print(f"Système : {reponse_propre}")
                        parler(reponse_propre)
                    else:
                        msg = "J'ouvre la page immédiatement."
                        print(f"Système : {msg}")
                        parler(msg)
                        
                except Exception as e:
                    erreur = "Erreur lors de l'ouverture."
                    print(f"Système : {erreur} ({e})")
                    parler(erreur)
            else:
                print(f"Système : {reponse_ia}")
                parler(reponse_ia)