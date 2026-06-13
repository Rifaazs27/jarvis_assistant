import ollama
import datetime
import webbrowser # Le module parfait et natif pour Windows

historique_conversation = [
    {
        'role': 'system', 
        'content': (
            "Tu es Jarvis, l'assistant personnel de mon ordinateur. "
            "Tu es brillant, direct et concis. "
            "RÈGLE SPÉCIALE : Si l'utilisateur te demande d'ouvrir un site web, de chercher un site ou d'aller sur internet, "
            "tu dois IMPÉRATIVEMENT inclure dans ta réponse la balise exacte : [OUVRIR: url_du_site]. "
            "Par exemple, si on te demande d'aller sur YouTube, tu dois répondre : Je m'en occupe. [OUVRIR: https://www.youtube.com]"
        )
    }
]

def demander_a_jarvis(texte_utilisateur):
    """Envoie le contexte complet à Ollama et récupère la réponse."""
    heure_actuelle = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    contexte_temporel = f"[Système : Nous sommes le {heure_actuelle}] "
    
    historique_conversation.append({
        'role': 'user', 
        'content': contexte_temporel + texte_utilisateur
    })
    
    try:
        reponse = ollama.chat(model='mistral', messages=historique_conversation)
        texte_reponse = reponse['message']['content']
        
        historique_conversation.append({
            'role': 'assistant', 
            'content': texte_reponse
        })
        
        return texte_reponse
    
    except Exception as e:
        historique_conversation.pop()
        return f"Erreur système Ollama : {e}"

if __name__ == "__main__":
    print("=====================================")
    print(" Jarvis v1.2 - Modules : [Mémoire] [Horloge] [Navigation Web Native]")
    print(" ('exit' pour quitter)")
    print("=====================================")
    
    while True:
        requete = input("\nToi : ")
        
        if requete.lower() in ['exit', 'quit', 'quitter']:
            print("Jarvis : Extinction des systèmes. À bientôt.")
            break
        
        reponse_jarvis = demander_a_jarvis(requete)
        
        # --- DÉTECTION ET EXÉCUTION DES ACTIONS ---
        if "[OUVRIR:" in reponse_jarvis:
            try:
                # 1. On extrait l'URL
                debut = reponse_jarvis.find("[OUVRIR:") + 8
                fin = reponse_jarvis.find("]", debut)
                url = reponse_jarvis[debut:fin].strip()
                
                # 2. On ouvre le navigateur proprement sous Windows
                webbrowser.open(url)
                
                # 3. On nettoie la phrase pour l'utilisateur
                reponse_propre = reponse_jarvis[:reponse_jarvis.find("[OUVRIR:")].strip()
                if reponse_propre:
                    print(f"Jarvis : {reponse_propre}")
                else:
                    print("Jarvis : J'ouvre la page immédiatement, monsieur.")
                    
            except Exception as e:
                print(f"Jarvis : Une erreur est survenue lors de l'ouverture du navigateur ({e}).")
        
        else:
            print(f"Jarvis : {reponse_jarvis}")