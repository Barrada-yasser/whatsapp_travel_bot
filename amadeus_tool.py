from amadeus_api import AmadeusAPI

def search_flights_tool(query: str) -> str:
    """
    Recherche vols réels via Amadeus API.
    
    Query format: "origin destination departure_date return_date"
    Exemple: "CMN CDG 2026-01-28 2026-01-30"
    """
    try:
        parts = query.split()
        
        if len(parts) < 3:
            return "❌ Format invalide. Utilise: origin destination departure_date [return_date]"
        
        origin = parts[0]
        destination = parts[1]
        departure_date = parts[2]
        return_date = parts[3] if len(parts) > 3 else None
        
        api = AmadeusAPI()
        
        result = api.search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            adults=1,
            max_results=5
        )
        
        return result if result else "❌ Aucun vol trouvé"
    
    except Exception as e:
        return f"❌ Erreur : {e}"

# Codes aéroports courants
AIRPORT_CODES = {
    "casablanca": "CMN",
    "paris": "CDG",
    "marrakech": "RAK",
    "rabat": "RBA",
    "new york": "JFK",
    "londres": "LHR",
    "madrid": "MAD",
    "barcelona": "BCN",
    "rome": "FCO",
    "istanbul": "IST",
    "dubai": "DXB"
}

def get_airport_code(city: str) -> str:
    """Convertit nom ville en code aéroport"""
    city_lower = city.lower().strip()
    return AIRPORT_CODES.get(city_lower, city.upper()[:3])