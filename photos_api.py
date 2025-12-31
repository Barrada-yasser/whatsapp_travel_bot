import os
import requests

class PhotosAPI:
    """
    Récupère photos haute qualité pour hôtels/villes
    """
    
    def __init__(self):
        self.access_key = os.getenv("UNSPLASH_ACCESS_KEY")
        self.base_url = "https://api.unsplash.com"
    
    def search_hotel_photos(self, city, hotel_name=None, count=3):
        """
        Recherche photos d'hôtels
        """
        if hotel_name:
            query = f"{hotel_name} hotel {city}"
        else:
            query = f"luxury hotel {city}"
        
        url = f"{self.base_url}/search/photos"
        
        params = {
            "query": query,
            "per_page": count,
            "orientation": "landscape"
        }
        
        headers = {
            "Authorization": f"Client-ID {self.access_key}"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            photos = []
            
            for result in data.get("results", []):
                photos.append({
                    "url": result["urls"]["regular"],
                    "thumb": result["urls"]["thumb"],
                    "description": result.get("alt_description", "Hôtel"),
                    "photographer": result["user"]["name"]
                })
            
            return photos
        
        except Exception as e:
            print(f"❌ Erreur photos : {e}")
            return []
    
    def search_city_photos(self, city, count=3):
        """
        Recherche photos de ville
        """
        url = f"{self.base_url}/search/photos"
        
        params = {
            "query": f"{city} landmarks architecture",
            "per_page": count,
            "orientation": "landscape"
        }
        
        headers = {
            "Authorization": f"Client-ID {self.access_key}"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            photos = []
            
            for result in data.get("results", []):
                photos.append({
                    "url": result["urls"]["regular"],
                    "thumb": result["urls"]["thumb"],
                    "description": result.get("alt_description", city),
                    "photographer": result["user"]["name"]
                })
            
            return photos
        
        except Exception as e:
            print(f"❌ Erreur photos : {e}")
            return []

# Test
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    api = PhotosAPI()
    
    print("📸 Test photos Paris...")
    
    # Photos hôtels Paris
    hotel_photos = api.search_hotel_photos("Paris", count=3)
    print(f"\n🏨 {len(hotel_photos)} photos d'hôtels trouvées")
    for i, photo in enumerate(hotel_photos, 1):
        print(f"{i}. {photo['description']}")
        print(f"   URL : {photo['url'][:50]}...")
    
    # Photos ville Paris
    city_photos = api.search_city_photos("Paris", count=3)
    print(f"\n🗼 {len(city_photos)} photos de Paris trouvées")
    for i, photo in enumerate(city_photos, 1):
        print(f"{i}. {photo['description']}")
        print(f"   URL : {photo['url'][:50]}...")