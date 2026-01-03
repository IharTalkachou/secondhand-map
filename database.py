import sqlite3
from geopy.geocoders import Nominatim
import time

from scraper import get_discounts_modamax

def init_db():
    conn = sqlite3.connect('shops.db')
    cursor = conn.cursor()
    
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS shops(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT,
            discount TEXT,
            lat REAL,
            lon REAL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )
    
    conn.commit()
    conn.close()

def get_coordinates(address):
    geolocator = Nominatim(user_agent='secondhand_map_pet_project')
    try:
        location = geolocator.geocode(address)
        if location:
            return location.latitude, location.longitude
    except Exception as e:
        print(f'Ошибка геокодинга для {address}: {e}')
    return None, None

def save_to_db(data_list):
    conn =sqlite3.connect('shops.db')
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM shops')
    
    print(f'Найдено {len(data_list)} магазинов. Обработка...')
    
    for item in data_list:
        address = item['address']
        discount = item['discount']
        
        if 'lat' not in item:
            lat, lon = get_coordinates(item['address'])
            time.sleep(1)
        else:
            lat, lon = item['lat'], item['lon']
        
        if lat and lon:
            cursor.execute(
                '''
                INSERT INTO shops (address, discount, lat, lon)
                VALUES (?, ?, ?, ?)
                ''',
                (address, discount, lat, lon)
            )
    
    conn.commit()
    conn.close()
    print('Данные сохранены в базе данных.')

if __name__ == '__main__':
    init_db()
    
    print('Парсинг с сайта...')
    scraped_data = get_discounts_modamax()
    
    if scraped_data:
        save_to_db(scraped_data)
    else:
        print('Парсинг не удался.')