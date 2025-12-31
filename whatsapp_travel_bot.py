import warnings
warnings.filterwarnings('ignore')

from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
from amadeus_api import AmadeusAPI
from photos_api import PhotosAPI
import time
import threading

load_dotenv()

app = Flask(__name__)

# Configuration Twilio
client = Client(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)

# Configuration Claude
claude_llm = LLM(
    model="anthropic/claude-sonnet-4-20250514",
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

# ========================================
# CRÉER LES AGENTS
# ========================================

trip_planner = Agent(
    role="Organisateur de Voyage Expert",
    goal="Créer voyage parfait coordonné",
    backstory="Agent de voyage avec 15 ans d'expérience.",
    verbose=False,
    llm=claude_llm,
    memory=False
)

flight_finder = Agent(
    role="Expert Recherche de Vols",
    goal="Trouver meilleurs vols",
    backstory="Expert vols avec accès Amadeus API.",
    verbose=False,
    llm=claude_llm,
    memory=False
)

hotel_matcher = Agent(
    role="Conseiller Hébergement Expert",
    goal="Trouver hôtels coordonnés",
    backstory="Expert hôtellerie mondiale.",
    verbose=False,
    llm=claude_llm,
    memory=False
)

print("✅ Agents créés")

# ========================================
# ÉTAT CONVERSATIONS
# ========================================

user_states = {}

def envoyer_whatsapp(to_number, message):
    """Envoie message WhatsApp"""
    try:
        message = client.messages.create(
            from_=os.getenv("TWILIO_WHATSAPP_NUMBER"),
            body=message,
            to=to_number
        )
        return True
    except Exception as e:
        print(f"❌ Erreur envoi : {e}")
        return False

def envoyer_photo(to_number, photo_url, caption=""):
    """Envoie photo WhatsApp"""
    try:
        message = client.messages.create(
            from_=os.getenv("TWILIO_WHATSAPP_NUMBER"),
            body=caption,
            media_url=[photo_url],
            to=to_number
        )
        return True
    except Exception as e:
        print(f"❌ Erreur photo : {e}")
        return False

def traiter_recherche(from_number, state):
    """
    Traite la recherche en arrière-plan
    """
    try:
        # Message d'attente
        envoyer_whatsapp(
            from_number,
            "⚙️ RECHERCHE EN COURS\n\n"
            "✈️ Je compare 400+ compagnies aériennes\n"
            f"🏨 Je cherche {'les meilleurs hôtels' if state['avec_hotel'] else 'pas d\'hôtel'}\n"
            "💰 J'optimise ton budget\n\n"
            "⏳ Patiente 2-3 minutes...\n"
            "Je te préviens dès que c'est prêt !"
        )
        
        # Créer tâches selon options
        if state['type_vol'] == 'aller-retour':
            flight_desc = f"Trouve meilleur vol ALLER-RETOUR de {state['depart']} vers {state['destination']}, dates {state['date_depart']} - {state['date_retour']}, budget {state['budget']}€"
        else:
            flight_desc = f"Trouve meilleur vol ALLER SIMPLE de {state['depart']} vers {state['destination']}, date {state['date_depart']}, budget {state['budget']}€"
        
        search_flights_task = Task(
            description=flight_desc,
            expected_output="Vol avec prix, horaires, durée",
            agent=flight_finder
        )
        
        tasks = [search_flights_task]
        context_tasks = [search_flights_task]
        
        if state['avec_hotel']:
            search_hotels_task = Task(
                description=f"Trouve meilleur hôtel à {state['destination']}, coordonné avec vol, budget restant environ {int(state['budget']) - 200}€",
                expected_output="Hôtel avec prix, localisation",
                agent=hotel_matcher,
                context=[search_flights_task]
            )
            tasks.append(search_hotels_task)
            context_tasks.append(search_hotels_task)
        
        create_package_task = Task(
            description=f"Crée package complet avec vol {'+ hôtel' if state['avec_hotel'] else 'seulement'} + prix total",
            expected_output="Package voyage résumé",
            agent=trip_planner,
            context=context_tasks
        )
        tasks.append(create_package_task)
        
        # Crew
        crew = Crew(
            agents=[trip_planner, flight_finder, hotel_matcher],
            tasks=tasks,
            process=Process.hierarchical,
            manager_llm=claude_llm,
            verbose=False,
            memory=False
        )
        
        # Lancer
        resultat = crew.kickoff()
        
        # Envoyer résultat
        envoyer_whatsapp(
            from_number,
            f"✅ PACKAGE TROUVÉ !\n\n{str(resultat)[:1200]}\n\n"
            "📸 Photos en envoi..."
        )
        
        # Envoyer photos destination
        photos_api = PhotosAPI()
        photos = photos_api.search_city_photos(state['destination'], count=3)
        
        for i, photo in enumerate(photos[:3], 1):
            envoyer_photo(
                from_number,
                photo['url'],
                f"📸 Photo {i}/3 - {state['destination']}"
            )
            time.sleep(1)  # Pause entre photos
        
        # Menu final
        envoyer_whatsapp(
            from_number,
            "💬 QUE VEUX-TU FAIRE ?\n\n"
            "✅ OUI - Je prends ce package\n"
            "🔄 AUTRE - Montre autre chose\n"
            "🆕 NOUVEAU - Autre destination"
        )
        
        state['step'] = 'menu'
        state['resultat'] = str(resultat)
        
    except Exception as e:
        print(f"❌ Erreur recherche: {e}")
        envoyer_whatsapp(
            from_number,
            f"❌ Erreur lors de la recherche.\n\nTape NOUVEAU pour réessayer"
        )

# ========================================
# WEBHOOK WHATSAPP
# ========================================

@app.route("/whatsapp", methods=['POST'])
def whatsapp_webhook():
    """
    Reçoit messages WhatsApp
    """
    incoming_msg = request.values.get('Body', '').strip()
    from_number = request.values.get('From', '')
    
    print(f"\n📱 Message de {from_number}: {incoming_msg}")
    
    resp = MessagingResponse()
    incoming_lower = incoming_msg.lower()
    
    # 🆕 MESSAGE D'INTRODUCTION AUTOMATIQUE
    if from_number not in user_states:
        user_states[from_number] = {'step': 'intro'}
        
        msg = resp.message()
        msg.body(
            "👋 Bienvenue sur TravelBot IA !\n\n"
            "Je peux t'organiser :\n"
            "✈️ Vols (aller simple ou retour)\n"
            "🏨 Hôtels\n"
            "📦 Packages complets\n\n"
            "💡 Je compare 400+ compagnies\n"
            "💡 Photos HD incluses\n"
            "💡 Meilleurs prix garantis\n\n"
            "🚀 Tape GO pour commencer !"
        )
        return str(resp)
    
    state = user_states[from_number]
    
    # Commande NOUVEAU
    if 'nouveau' in incoming_lower or state['step'] == 'intro':
        state['step'] = 'destination'
        
        msg = resp.message()
        msg.body(
            "✈️ C'EST PARTI !\n\n"
            "📍 Quelle est ta destination ?\n"
            "Exemple : Paris, New York, Londres, Tokyo..."
        )
        return str(resp)
    
    # Étape 1 : Destination
    if state['step'] == 'destination':
        state['destination'] = incoming_msg.title()
        state['step'] = 'depart'
        
        msg = resp.message()
        msg.body(
            f"✅ Destination : {state['destination']}\n\n"
            "✈️ D'où tu pars ?\n"
            "Exemple : Casablanca, Fez, Marrakech..."
        )
    
    # Étape 2 : Ville départ
    elif state['step'] == 'depart':
        state['depart'] = incoming_msg.title()
        state['step'] = 'type_vol'
        
        msg = resp.message()
        msg.body(
            f"✅ De : {state['depart']}\n"
            f"✅ À : {state['destination']}\n\n"
            "✈️ TYPE DE VOL ?\n\n"
            "1️⃣ Aller-retour\n"
            "2️⃣ Aller simple\n\n"
            "Réponds : 1 ou 2"
        )
    
    # 🆕 Étape 3 : Type de vol
    elif state['step'] == 'type_vol':
        if '1' in incoming_lower or 'retour' in incoming_lower:
            state['type_vol'] = 'aller-retour'
            state['step'] = 'dates_ar'
            
            msg = resp.message()
            msg.body(
                "✅ Aller-retour sélectionné\n\n"
                "📅 Dates de voyage ?\n"
                "Format : JJ/MM - JJ/MM\n"
                "Exemple : 28/01 - 30/01"
            )
        elif '2' in incoming_lower or 'simple' in incoming_lower:
            state['type_vol'] = 'aller-simple'
            state['step'] = 'date_as'
            
            msg = resp.message()
            msg.body(
                "✅ Aller simple sélectionné\n\n"
                "📅 Date de départ ?\n"
                "Format : JJ/MM\n"
                "Exemple : 28/01"
            )
        else:
            msg = resp.message()
            msg.body("❌ Réponds 1 (aller-retour) ou 2 (aller simple)")
    
    # Étape 4a : Dates aller-retour
    elif state['step'] == 'dates_ar':
        try:
            dates = incoming_msg.split('-')
            state['date_depart'] = dates[0].strip()
            state['date_retour'] = dates[1].strip()
            state['step'] = 'avec_hotel'
            
            msg = resp.message()
            msg.body(
                f"✅ Départ : {state['date_depart']}\n"
                f"✅ Retour : {state['date_retour']}\n\n"
                "🏨 BESOIN D'UN HÔTEL ?\n\n"
                "✅ OUI - Vol + Hôtel\n"
                "❌ NON - Juste le vol\n\n"
                "Réponds : OUI ou NON"
            )
        except:
            msg = resp.message()
            msg.body(
                "❌ Format incorrect.\n\n"
                "Utilise : JJ/MM - JJ/MM\n"
                "Exemple : 28/01 - 30/01"
            )
    
    # Étape 4b : Date aller simple
    elif state['step'] == 'date_as':
        state['date_depart'] = incoming_msg.strip()
        state['date_retour'] = None
        state['step'] = 'avec_hotel'
        
        msg = resp.message()
        msg.body(
            f"✅ Départ : {state['date_depart']}\n\n"
            "🏨 BESOIN D'UN HÔTEL ?\n\n"
            "✅ OUI - Vol + Hôtel\n"
            "❌ NON - Juste le vol\n\n"
            "Réponds : OUI ou NON"
        )
    
    # 🆕 Étape 5 : Avec ou sans hôtel
    elif state['step'] == 'avec_hotel':
        if 'oui' in incoming_lower or '✅' in incoming_lower:
            state['avec_hotel'] = True
            msg = resp.message()
            msg.body(
                "✅ Vol + Hôtel\n\n"
                "💰 Quel est ton BUDGET TOTAL (en €) ?\n"
                "Exemple : 500"
            )
        elif 'non' in incoming_lower or '❌' in incoming_lower:
            state['avec_hotel'] = False
            msg = resp.message()
            msg.body(
                "✅ Juste le vol\n\n"
                "💰 Quel est ton BUDGET VOL (en €) ?\n"
                "Exemple : 200"
            )
        else:
            msg = resp.message()
            msg.body("❌ Réponds OUI ou NON")
        
        state['step'] = 'budget'
    
    # Étape 6 : Budget
    elif state['step'] == 'budget':
        try:
            state['budget'] = incoming_msg.replace('€', '').strip()
            state['step'] = 'processing'
            
            msg = resp.message()
            msg.body(
                "📋 RÉCAPITULATIF\n\n"
                f"📍 {state['depart']} → {state['destination']}\n"
                f"✈️ {state['type_vol'].title()}\n"
                f"📅 {state['date_depart']}{' - ' + state['date_retour'] if state.get('date_retour') else ''}\n"
                f"🏨 {'Avec hôtel' if state['avec_hotel'] else 'Sans hôtel'}\n"
                f"💰 Budget : {state['budget']}€\n\n"
                "✅ Tout est OK ?\n\n"
                "🚀 Tape OUI pour lancer la recherche"
            )
            state['step'] = 'confirm'
        
        except:
            msg = resp.message()
            msg.body("❌ Budget invalide. Entre un nombre : 500")
    
    # Étape 7 : Confirmation
    elif state['step'] == 'confirm':
        if 'oui' in incoming_lower:
            msg = resp.message()
            msg.body("🚀 Recherche lancée ! Patiente 2-3 min...")
            
            # Lancer recherche en arrière-plan
            thread = threading.Thread(target=traiter_recherche, args=(from_number, state))
            thread.start()
            
            state['step'] = 'waiting'
        else:
            msg = resp.message()
            msg.body("❌ Recherche annulée.\n\nTape NOUVEAU pour recommencer")
    
    # Étape 8 : Menu final
    elif state['step'] == 'menu':
        if 'oui' in incoming_lower or 'prends' in incoming_lower:
            msg = resp.message()
            msg.body(
                "🎉 SUPER CHOIX !\n\n"
                "📋 PROCHAINES ÉTAPES :\n\n"
                "1️⃣ VOL\n"
                "Cherche sur Google Flights ou Skyscanner\n"
                "avec les infos ci-dessus\n\n"
                + ("2️⃣ HÔTEL\n"
                "Cherche sur Booking.com\n\n" if state['avec_hotel'] else "") +
                "✈️ Bon voyage !\n\n"
                "Tape NOUVEAU pour autre destination"
            )
        
        elif 'autre' in incoming_lower:
            msg = resp.message()
            msg.body("🔄 Nouvelle recherche lancée...")
            state['step'] = 'confirm'
            thread = threading.Thread(target=traiter_recherche, args=(from_number, state))
            thread.start()
        
        elif 'nouveau' in incoming_lower:
            del user_states[from_number]
            msg = resp.message()
            msg.body(
                "🆕 Nouvelle recherche !\n\n"
                "📍 Quelle destination ?"
            )
    
    else:
        msg = resp.message()
        msg.body(
            "❓ Message non reconnu.\n\n"
            "Tape NOUVEAU pour recommencer"
        )
    
    return str(resp)

@app.route("/status", methods=['GET'])
def status():
    return "✅ Travel Bot actif !"

# ========================================
# LANCEMENT
# ========================================

if __name__ == "__main__":
    print("="*50)
    print("✈️ TRAVEL BOT WHATSAPP V2 DÉMARRÉ")
    print("="*50)
    print("📱 En attente de messages...")
    print("\n🆕 AMÉLIORATIONS :")
    print("  ✅ Message intro automatique")
    print("  ✅ Choix aller simple/retour")
    print("  ✅ Choix avec/sans hôtel")
    print("  ✅ Message d'attente")
    
    app.run(port=5000, debug=True)


