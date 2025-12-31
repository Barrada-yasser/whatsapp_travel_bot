from photos_api import PhotosAPI

def format_travel_package_with_photos(package_text, destination):
    """
    Ajoute photos au package voyage
    """
    api = PhotosAPI()
    
    # Photos destination
    city_photos = api.search_city_photos(destination, count=3)
    
    # Photos hôtels
    hotel_photos = api.search_hotel_photos(destination, count=3)
    
    result = package_text + "\n\n"
    result += "="*60 + "\n"
    result += "📸 GALERIE PHOTOS\n"
    result += "="*60 + "\n\n"
    
    # Photos ville
    result += f"🗼 PHOTOS {destination.upper()}\n\n"
    for i, photo in enumerate(city_photos, 1):
        result += f"{i}. {photo['description']}\n"
        result += f"   {photo['url']}\n\n"
    
    # Photos hôtels
    result += f"\n🏨 PHOTOS HÔTELS {destination.upper()}\n\n"
    for i, photo in enumerate(hotel_photos, 1):
        result += f"{i}. {photo['description']}\n"
        result += f"   {photo['url']}\n\n"
    
    return result