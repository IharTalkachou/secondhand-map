import sqlite3
from geopy import Photon, Nominatim
import time

from scraper import get_discounts

CORRECTIONS = {
    'Минск, ул. Ангарская, 36А': (53.871291, 27.685107),
    'Минск, ул. Алибегова, 13/1': (53.871037, 27.473608),
    'Минск, ул. Я. Коласа, 33': (53.924654, 27.591547)
}

def init_db():
    conn = sqlite3.connect('shops.db')
    cursor = conn.cursor()
    
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS shops(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_name TEXT,
            address TEXT,
            discount TEXT,
            color TEXT,
            lat REAL,
            lon REAL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )
    
    conn.commit()
    conn.close()

def get_coordinates(address):
    # Проверяю наличие координат для адреса в CORRECTIONS
    if address in CORRECTIONS:
        print(f'   [!] Применена ручная правка для: {address}')
        return CORRECTIONS[address]
    
    # Если правленного адреса нет, опрашиваю Nominatum
    geolocator = Nominatim(user_agent='secondhand_map_pet_project')
    
    # очистка адреса для улучшения поисковых возможностей
    clean_address = address.\
        replace('г.', '').\
        replace('ул.', '').\
        replace('пр-т', '').\
        replace('тр-т', '').\
        replace('/', ' к')
    # для точности добавлю Минск в поисковый запрос
    if 'Минск' not in clean_address:
        search_query = f'Минск, {clean_address}'
    else:
        search_query = clean_address
    
    try:
        location = geolocator.geocode(search_query, limit=1)
        
        if location:
            # вывод этапов поиска для отладки
            print(f'  [Check] Запрос для поиска: {search_query} > Результат: {location.address}')
                       
            return location.latitude, location.longitude
        else:
            print(f"  [Warn] Nominatum ничего не нашел по запросу: {search_query}")
            
    except Exception as e:
        print(f'  [Error] Ошибка геокодинга для {address}: {e}')
    
    return None, None

def save_to_db(data_list):
    conn =sqlite3.connect('shops.db')
    cursor = conn.cursor()
    
    # таблицу очищаем для исключения дублирования записей и обновления координат
    cursor.execute('DELETE FROM shops')
    
    print(f'Найдено {len(data_list)} магазинов. Обработка базы...')
    
    for item in data_list:
        shop_name = item.get('shop_name', 'Unknown')
        address = item['address']
        discount = item['discount']
        color = item.get('color', 'gray')
        
        print(f"Обработка: {address}")
        lat, lon = get_coordinates(address)
        
        if lat and lon:
            cursor.execute(
                '''
                INSERT INTO shops (shop_name, address, discount, color, lat, lon)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (shop_name, address, discount, color, lat, lon)
            )
        # добавляю паузу если шло обращение к Nominatum = нет адреса в CORRECTIONS
        if address not in CORRECTIONS:
            time.sleep(1)
        
    conn.commit()
    conn.close()
    print('Данные сохранены в базе данных.')

if __name__ == '__main__':
    init_db()
    
    print('Парсинг данных с сайтов...')
    all_data = get_discounts()
    
    if all_data:
        save_to_db(all_data)
    else:
        print('Парсинг не удался или список пуст.')