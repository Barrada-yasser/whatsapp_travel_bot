from photos_api import PhotosAPI

def get_hotel_photos_tool(city: str, hotel_name: str = None) -> str:
    """
    Récupère photos d'hôtels pour présentation visuelle
    """
    api = PhotosAPI()
    
    photos = api.search_hotel_photos(city, hotel_name, count=3)
    
    if not photos:
        return "❌ Aucune photo trouvée"
    
    result = f"📸 PHOTOS HÔTEL {city.upper()}\n\n"
    
    for i, photo in enumerate(photos, 1):
        result += f"{i}. {photo['description']}\n"
        result += f"   🔗 {photo['url']}\n\n"
    
    return result

def get_city_photos_tool(city: str) -> str:
    """
    Récupère photos de la ville destination
    """
    api = PhotosAPI()
    
    photos = api.search_city_photos(city, count=3)
    
    if not photos:
        return "❌ Aucune photo trouvée"
    
    result = f"📸 PHOTOS {city.upper()}\n\n"
    
    for i, photo in enumerate(photos, 1):
        result += f"{i}. {photo['description']}\n"
        result += f"   🔗 {photo['url']}\n\n"
    
    return result