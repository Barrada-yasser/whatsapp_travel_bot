import os
import requests
from datetime import datetime

class AmadeusAPI:
    """
    Interface pour Amadeus Flight API
    """
    
    def __init__(self):
        self.api_key = os.getenv("AMADEUS_API_KEY")
        self.api_secret = os.getenv("AMADEUS_API_SECRET")
        self.base_url = "https://test.api.amadeus.com/v2"
        self.token = None
    
    def get_token(self):
        """
        Obtenir token d'authentification
        """
        url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        
        data = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.api_secret
        }
        
        try:
            response = requests.post(url, data=data)
            response.raise_for_status()
            self.token = response.json()["access_token"]
            return True
        except Exception as e:
            print(f"❌ Erreur authentification : {e}")
            return False
    
    def search_flights(self, origin, destination, departure_date, return_date=None, adults=1, max_results=5):
        """
        Recherche vols réels
        """
        if not self.token:
            if not self.get_token():
                return None
        
        url = f"{self.base_url}/shopping/flight-offers"
        
        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date,
            "adults": adults,
            "max": max_results,
            "currencyCode": "EUR"
        }
        
        if return_date:
            params["returnDate"] = return_date
        
        headers = {
            "Authorization": f"Bearer {self.token}"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return self.format_flights(response.json())
        except Exception as e:
            print(f"❌ Erreur recherche vols : {e}")
            return None
    
    def format_flights(self, data):
        """
        Formate résultats API en texte lisible
        """
        if not data.get("data"):
            return "❌ Aucun vol trouvé"
        
        flights_text = "✈️ VOLS TROUVÉS :\n\n"
        
        for i, offer in enumerate(data["data"][:3], 1):
            price = offer["price"]["total"]
            
            # Premier segment (aller)
            outbound = offer["itineraries"][0]
            segments = outbound["segments"]
            
            departure = segments[0]["departure"]
            arrival = segments[-1]["arrival"]
            
            dep_time = departure["at"].split("T")[1][:5]
            arr_time = arrival["at"].split("T")[1][:5]
            
            duration = outbound["duration"].replace("PT", "").replace("H", "h").replace("M", "min")
            
            stops = len(segments) - 1
            airlines = segments[0]["carrierCode"]
            
            flights_text += f"{i}. {airlines} - {price}€\n"
            flights_text += f"   {departure['iataCode']} {dep_time} → {arrival['iataCode']} {arr_time}\n"
            flights_text += f"   Durée: {duration} | Escales: {stops}\n\n"
        
        return flights_text

# Test
# Test
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    api = AmadeusAPI()
    
    print("🔑 Test authentification...")
    if api.get_token():
        print("✅ Token obtenu !")
        
        print("\n✈️ Test recherche vols...")
        result = api.search_flights(
            origin="CMN",  # Casablanca
            destination="CDG",  # Paris
            departure_date="2026-01-28",  # 🔥 Date future
            return_date="2026-01-30",     # 🔥 Date future
            adults=1
        )
        
        print(result)
    else:
        print("❌ Erreur authentification")