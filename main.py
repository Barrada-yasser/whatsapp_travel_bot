import warnings
warnings.filterwarnings('ignore')

import os
from crewai import Agent, Task, Crew, Process, LLM
from dotenv import load_dotenv

# Charger variables
load_dotenv()

# Configuration Claude
claude_llm = LLM(
    model="anthropic/claude-sonnet-4-20250514",
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

print("="*50)
print("✈️ TRAVEL BOT - CONFIGURATION")
print("="*50)
print("✅ Claude LLM configuré")
print("✅ Prêt pour créer les agents")

# ========================================
# AGENT 1 : TRIP PLANNER (MANAGER)
# ========================================

trip_planner = Agent(
    role="Organisateur de Voyage Expert",
    goal="Créer voyage parfait coordonné (vol + hôtel + activités)",
    backstory=(
        "Agent de voyage avec 15 ans d'expérience. "
        "Tu connais tous les trucs pour optimiser voyages : "
        "meilleurs vols, hôtels bien situés, timing parfait. "
        "Tu coordonnes tout pour que ça s'enchaîne parfaitement."
    ),
    verbose=True,
    llm=claude_llm,
    memory=False
)

print("✅ Agent Trip Planner créé")

# ========================================
# AGENT 2 : FLIGHT FINDER
# ========================================

flight_finder = Agent(
    role="Expert Recherche de Vols",
    goal="Trouver les meilleurs vols RÉELS via Amadeus API",
    backstory=(
        "Expert vols avec accès API Amadeus (400+ compagnies). "
        "Tu recherches vols réels avec prix actuels. "
        "Format recherche: origine (code 3 lettres) destination date_depart date_retour. "
        "Exemples codes: CMN=Casablanca, CDG=Paris, JFK=New York. "
        "Dates format: YYYY-MM-DD"
    ),
    verbose=True,
    llm=claude_llm,
    memory=False
)

print("✅ Agent Flight Finder créé (avec accès API Amadeus)")

# ========================================
# AGENT 3 : HOTEL MATCHER (AVEC PHOTOS)
# ========================================

hotel_matcher = Agent(
    role="Conseiller Hébergement Expert avec Photos",
    goal="Trouver hôtels coordonnés avec les vols + fournir photos",
    backstory=(
        "Expert hôtellerie mondiale avec accès photos professionnelles. "
        "Tu sélectionnes hôtels selon : emplacement, qualité, prix. "
        "Tu assures coordination parfaite avec dates vols."
    ),
    verbose=True,
    llm=claude_llm,
    memory=False
)

print("✅ Agent Hotel Matcher créé (avec photos)")

print("\n" + "="*50)
print("🎉 3 AGENTS CRÉÉS !")
print("="*50)

# ========================================
# TÂCHE DE TEST
# ========================================

trip_request = {
    "depart": "Casablanca",
    "destination": "Paris",
    "date_depart": "28 janvier 2026",
    "date_retour": "30 janvier 2026",
    "budget": "500€",
    "voyageurs": "1 adulte"
}

print("\n📋 Données de test :")
print(f"   De : {trip_request['depart']}")
print(f"   À : {trip_request['destination']}")
print(f"   Départ : {trip_request['date_depart']}")
print(f"   Retour : {trip_request['date_retour']}")
print(f"   Budget : {trip_request['budget']}")

# Tâche 1 : Recherche vols
search_flights_task = Task(
    description=(
        f"Trouve les meilleurs vols de {trip_request['depart']} "
        f"à {trip_request['destination']}.\n"
        f"Dates : {trip_request['date_depart']} → {trip_request['date_retour']}\n"
        f"Budget max : {trip_request['budget']}\n\n"
        "Propose 2 options :\n"
        "1. Option économique (vol le moins cher)\n"
        "2. Option confort (meilleur rapport qualité/prix)\n\n"
        "Pour chaque option indique :\n"
        "- Compagnie\n"
        "- Horaires\n"
        "- Prix\n"
        "- Durée"
    ),
    expected_output="2 options de vols avec détails complets",
    agent=flight_finder
)

# Tâche 2 : Recherche hôtels (AVEC PHOTOS)
search_hotels_task = Task(
    description=(
        f"Trouve 2 hôtels à {trip_request['destination']}.\n"
        f"Dates : {trip_request['date_depart']} → {trip_request['date_retour']}\n"
        f"Budget : Environ 300€ pour 2 nuits\n\n"
        "Pour chaque hôtel indique :\n"
        "- Nom et étoiles\n"
        "- Quartier\n"
        "- Prix par nuit\n"
        "- Avantages"
    ),
    expected_output="2 hôtels avec détails",
    agent=hotel_matcher,
    context=[search_flights_task]
)

# Tâche 3 : Créer package complet
create_package_task = Task(
    description=(
        "Crée un package voyage complet coordonné.\n\n"
        "Combine :\n"
        "- Meilleur vol trouvé\n"
        "- Meilleur hôtel trouvé\n\n"
        "Vérifie la cohérence :\n"
        "- Hôtel réservé nuit d'arrivée\n"
        "- Checkout avant vol retour\n\n"
        "Calcule prix total et donne résumé clair."
    ),
    expected_output="Package voyage complet avec prix total",
    agent=trip_planner,
    context=[search_flights_task, search_hotels_task]
)

print("\n✅ 3 tâches créées")

# Créer la Crew
travel_crew = Crew(
    agents=[trip_planner, flight_finder, hotel_matcher],
    tasks=[search_flights_task, search_hotels_task, create_package_task],
    process=Process.hierarchical,
    manager_llm=claude_llm,
    verbose=True,
    memory=False
)

print("✅ Crew créée")
print("\n" + "="*50)
print("🚀 PRÊT À TESTER AVEC PHOTOS")
print("="*50)

# ========================================
# LANCEMENT AVEC PHOTOS
# ========================================

from format_output import format_travel_package_with_photos

print("\n🚀 Lancement des agents...")

# Lancer UNE SEULE FOIS
resultat = travel_crew.kickoff(inputs=trip_request)

# Ajouter photos au résultat
resultat_avec_photos = format_travel_package_with_photos(
    str(resultat), 
    trip_request['destination']
)

print("\n" + "="*60)
print("✅ PACKAGE VOYAGE COMPLET AVEC PHOTOS")
print("="*60)
print(resultat_avec_photos)