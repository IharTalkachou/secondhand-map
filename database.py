import sqlite3
from geopy import Nominatim
import time

from scraper import get_discounts

CORRECTIONS = {
    'Минск, ул. Ангарская, 36А': (53.871291, 27.685107),
    'Минск, ул. Алибегова, 13/1': (53.871037, 27.473608),
    'Минск, ул. Я. Коласа, 33': (53.924654, 27.591547),
    'Молодечно, ул. В. Гостинец, 54': (54.307416, 26.829399),
    'Минск, ул. Калиновского, 55 (1 этаж)': (53.947219, 27.628711),
    'Минск, ул.Романовская Слобода, 12': (53.903292, 27.546281)
}

def init_db():
    conn = sqlite3.connect('shops.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_name TEXT,
            address TEXT,
            discount TEXT,
            color TEXT, 
            lat REAL,
            lon REAL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(shop_name, address)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_coordinates(address):
    # Проверяю наличие координат для адреса в CORRECTIONS
    if address in CORRECTIONS:
        print(f'   [!] Применена ручная правка для: {address}')
        return CORRECTIONS[address]
    
    # Если правленного адреса нет буду опрашивать Nominatum
    # создаю объект геолокатора
    geolocator = Nominatim(user_agent='secondhand_map_pet_project')
    
    # очистка адреса для улучшения поисковых возможностей
    clean_address = address.\
        replace('г.', '').\
        replace('ул.', '').\
        replace('пр-т', '').\
        replace('тр-т', '').\
        replace('/', ' к')
         
    try:
        location = geolocator.geocode(clean_address)
        
        if location:
            # вывод этапов поиска для отладки
            print(f'  [Check] Запрос для поиска: {clean_address} > Результат: {location.address}')
                       
            return location.latitude, location.longitude
        else:
            print(f"  [Warn] Nominatum ничего не нашел по запросу: {clean_address}")
            
    except Exception as e:
        print(f'  [Error] Ошибка геокодинга для {address}: {e}')
    
    return None, None

def save_to_db(scraped_data):
    conn =sqlite3.connect('shops.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print(f'\n--- Начало обновления базы данных ---')
    
    # проверка существования дубликатов
    # если парсер вернул неуникальную ПАРУ (название, адрес), учитываем только первую
    unique_data = []
    seen_in_batch = set()
    
    for item in scraped_data:
        unique_key = (item.get('shop_name', 'Unknown'), item['address'])
        
        if unique_key not in seen_in_batch:
            unique_data.append(item)
            seen_in_batch.add(unique_key)
        else:
            print(f'  [Warn] Дубликат в данных парсера: {unique_key}. Игнорируется.')
    
    scraped_data = unique_data
    
    # загрузка существующей базы в память
    # создается словать {('название', 'адрес'): row_id}
    existing_shops = {} 
    cursor.execute('SELECT id, shop_name, address FROM shops')
    for row in cursor.fetchall():
        key = (row['shop_name'], row['address'])
        existing_shops[key] = row['id']
    
    print(f'В базе данных найдено {len(existing_shops)} магазинов.')
    
    # далее - список ПАР (название, адрес), которые обработаны в этом запуске (чтобы удалить лишнее)
    processed_keys = []
    
    # счётчики - для статистики
    cnt_updated = 0
    cnt_inserted = 0
    cnt_error = 0
    
    # обработка новых данных    
    for item in scraped_data:
        shop_name = item.get('shop_name', 'Unknown')
        address = item['address']
        discount = item['discount']
        color = item.get('color', 'gray')
        
        current_key = (shop_name, address)
        processed_keys.append(current_key)
        
        # логика А: магазин уже есть в базе 
        # (UPDATE) обновляются скидка, цвет и время; 
        # координаты заново не собираем
        if current_key in existing_shops:
            cursor.execute('''
                UPDATE shops
                SET discount = ?, color = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE shop_name = ? AND address = ?
            ''', (discount, color, shop_name, address))
            cnt_updated += 1
        
        # логика Б: магазин по новому адресу или новый магазин сети по существующему адресу
        # (INSERT) добавляем магазин, делаем геокодирование
        else:
            print(f' [New] Найден новый магазин {shop_name} по адресу {address}')
            lat, lon = get_coordinates(address)
            
            if lat and lon:
                cursor.execute('''
                    INSERT INTO shops (shop_name, address, discount, color, lat, lon)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (shop_name, address, discount, color, lat, lon))
                cnt_inserted += 1
                
                if address not in CORRECTIONS:
                    time.sleep(1)
            else:
                print(f' [Warn] {shop_name}: Не удалось найти координаты \
                    для нового магазина {address}')
                cnt_error += 1
    
    # логика В: адрес есть в существующих, но его нет в обработанных - магазина больше нет на сайте
    # (DELETE) удаляем магазин по адресу из базы данных
    cnt_deleted = 0
    for old_key, old_id in existing_shops.items():
        if old_key not in processed_keys:
            print(f'  [Warn] Магазин {old_key} больше не существует, удаляется.')
            cursor.execute('DELETE FROM shops WHERE id = ?', (old_id,))
            cnt_deleted += 1
    
    conn.commit()
    conn.close()
    
    print(f'\n --- Статистика ---')
    print(f"Всего получено от парсера: {len(scraped_data)}")
    print(f"Обновлено (без геокодинга): {cnt_updated}")
    print(f"Добавлено новых: {cnt_inserted}")
    print(f"Удалено старых: {cnt_deleted}")
    print(f"Ошибок геокодинга: {cnt_error}")
           
if __name__ == '__main__':
    init_db()
    
    print('Парсинг данных с сайтов...')
    all_data = get_discounts()
    
    if all_data:
        save_to_db(all_data)
    else:
        print('Парсинг не удался или список пуст.')