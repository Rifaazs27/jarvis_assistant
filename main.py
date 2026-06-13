import ollama
import datetime
import webbrowser
import pyttsx3
import speech_recognition as sr
import re

def parler(texte):
    """Fait parler Jarvis. Le moteur est initialisé à la volée pour la stabilité."""
    try:
        moteur = pyttsx3.init()
        moteur.setProperty('rate', 170)
        
        # Supprime les balises [OUVRIR:...] pour que la voix ne les lise pas
        texte_propre = re.sub(r'\[.*?\]', '', texte).strip()
        
        if texte_propre:
            moteur.say(texte_propre)
            moteur.runAndWait()
    except Exception as e:
        print(f"[Erreur vocale Windows : {e}]")

# --- CONFIGURATION DE L'AUDITION ---
recognizer = sr.Recognizer()

def ecouter():
    with sr.Microphone() as source:
        print("\n[Jarvis écoute... Parle maintenant]")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            texte = recognizer.recognize_google(audio, language="fr-FR")
            print(f"Toi : {texte}")
            return texte
        except sr.WaitTimeoutError:
            return ""
        except sr.UnknownValueError:
            # FIX 1 : On fait parler Jarvis ici avant de retourner la valeur vide
            msg_incomprehension = "Je n'ai pas bien compris."
            print(f"\n[Jarvis : {msg_incomprehension}]")
            parler(msg_incomprehension)
            return ""
        except Exception as e:
            print(f"\n[Erreur micro : {e}]")
            return ""

# --- LA MÉMOIRE & LE CERVEAU ---
historique_conversation = [
    {
        'role': 'system', 
        'content': (
            "Tu es Jarvis, l'assistant IA de mon ordinateur. "
            "RÈGLE 1 : Si on te demande d'OUVRIR ou d'ALLER sur un site web, tu DOIS ajouter la balise [OUVRIR: url]. "
            "RÈGLE 2 : Tu es physiquement INCAPABLE de fermer des pages, des onglets ou des applications. "
            "RÈGLE 3 : Si on te demande de FERMER quelque chose, tu devez répondre 'Désolé, je ne sais pas encore fermer de fenêtres' SANS utiliser aucune balise."
        )
    }
]

def demander_a_jarvis(texte_utilisateur):
    heure_actuelle = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    contexte_temporel = f"[Système : Nous sommes le {heure_actuelle}] "
    
    historique_conversation.append({
        'role': 'user', 
        'content': contexte_temporel + texte_utilisateur
    })
    
    try:
        reponse = ollama.chat(model='mistral', messages=historique_conversation)
        texte_reponse = reponse['message']['content']
        historique_conversation.append({'role': 'assistant', 'content': texte_reponse})
        return texte_reponse
    except Exception as e:
        historique_conversation.pop()
        return f"Erreur système Ollama : {e}"

# --- BOUCLE PRINCIPALE ---
if __name__ == "__main__":
    print("=====================================")
    print(" Jarvis v1.4.3 - Fix: Audio Incompréhension & Multi-onglets")
    print("=====================================")
    
    parler("Correctifs appliqués, monsieur.")
    
    while True:
        requete = ecouter()
        
        if not requete:
            continue
            
        if requete.lower() in ['exit', 'quit', 'quitter', 'désactiver', 'arrête-toi']:
            message_fin = "Extinction des systèmes. À bientôt monsieur."
            print(f"Jarvis : {message_fin}")
            parler(message_fin)
            break
        
        reponse_jarvis = demander_a_jarvis(requete)
        
        if "[OUVRIR:" in reponse_jarvis:
            try:
                debut = reponse_jarvis.find("[OUVRIR:") + 8
                fin = reponse_jarvis.find("]", debut)
                url = reponse_jarvis[debut:fin].strip()
                
                # FIX 2 : On force l'ouverture d'un seul onglet unique
                webbrowser.open_new_tab(url)
                
                reponse_propre = reponse_jarvis[:reponse_jarvis.find("[OUVRIR:")].strip()
                if reponse_propre:
                    print(f"Jarvis : {reponse_propre}")
                    parler(reponse_propre)
                else:
                    msg = "J'ouvre la page immédiatement."
                    print(f"Jarvis : {msg}")
                    parler(msg)
                    
            except Exception as e:
                erreur = "Erreur lors de l'ouverture du navigateur."
                print(f"Jarvis : {erreur} ({e})")
                parler(erreur)
        else:
            print(f"Jarvis : {reponse_jarvis}")
            parler(reponse_jarvis)