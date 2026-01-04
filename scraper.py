import requests
from bs4 import BeautifulSoup
import re
import cloudscraper

def get_profit_color(discount_text):
    '''
    Функция задания логики определения цвета точки на карте
    в зависимости от текста информации о цене/скидке
    '''
    text_lower = discount_text.lower()
    # логика раскраски для задания цен за килограмм
    if 'руб/кг' in text_lower:
        prices = re.findall(r"(\d+[\.,]?\d*)", text_lower)
        if prices:
            price = float(prices[0].replace(',', '.'))
            if price < 30: return 'green'
            if price < 60: return 'orange'
            return 'red'
    
    # логика раскраски для задания цен за вещь
    if 'руб/вещь' in text_lower:
        prices = re.findall(r"(\d+[\.,]?\d*)", text_lower)
        if prices:
            price = float(prices[0].replace(',', '.'))
            if price < 4: return 'green'
            if price < 7: return 'orange'
            return 'red'
        
    # логика раскраски для задания процентов скидки
    if '%' in text_lower:
        percents = re.findall(r"(\d+)", text_lower)
        if percents:
            val = int(percents[0])
            if val > 50: return 'green'
            if val > 20: return 'orange'
            return 'red'
    
    return 'gray'

def get_discounts_modamax():
    '''
    Функция получения действующих предложений от сети МодаМакс
    '''
    url = "https://modamax.by/price/minsk"
    
    print(f"  -> МодаМакс: Скачиваем через CloudScraper...")
    results = []
    
    try:
        # Создаем скрапер, который эмулирует Chrome
        scraper = cloudscraper.create_scraper() 
        
        # Делаем простой запрос. Скрапер сам разберется с заголовками и шифрованием.
        response = scraper.get(url)
        
        if response.status_code != 200:
            print(f"  [Error] МодаМакс: Ошибка доступа: {response.status_code}")
            return []
            
        html_text = response.text
        
        # --- ДИАГНОСТИКА (чтобы убедиться, что скачали всё) ---
        print(f"  [Debug] МодаМакс: Скачано байт: {len(html_text)}")
        
        # Парсинг
        soup = BeautifulSoup(html_text, 'html.parser')
        
        # Ищем строки таблицы
        rows = soup.find_all('div', class_='PriceTable__row')
        print(f"  [Debug] МодаМакс: Найдено строк PriceTable__row: {len(rows)}")
        
        if len(rows) == 0:
            print("  [Warn] МодаМакс: Таблица не найдена. Возможно, сервер прислал заглушку.")
            # Можно сохранить файл для проверки, если снова будет 0
            # with open("debug_scraper.html", "w", encoding="utf-8") as f: f.write(html_text)
            return []

        # Разбор строк
        for row in rows:
            try:
                # 1. Адрес
                addr_tag = row.find('a', class_='PriceTable__link')
                if not addr_tag: continue
                address = addr_tag.text.strip()
                
                # 2. Цена
                today_col = row.find('div', class_='PriceTable__col--today')
                discount_text = "-"
                
                if today_col:
                    amount_div = today_col.find('div', class_='PriceTable__amount-numbers')
                    if amount_div:
                        rub = amount_div.contents[0].strip()
                        coins_span = amount_div.find('span', class_='PriceTable__amount-coins')
                        coins = coins_span.text.strip() if coins_span else "00"
                        discount_text = f"{rub}.{coins} руб/кг"
                    else:
                        icon = today_col.find('img')
                        if icon and icon.get('alt'):
                            discount_text = icon.get('alt')
                        else:
                            discount_text = "Спецпредложение"
                
                # Фильтр закрытых магазинов
                if "не работает" in discount_text.lower() or discount_text == "-":
                    continue

                results.append({
                    "shop_name": "ModaMax",
                    "address": address,
                    "discount": discount_text,
                    "color": get_profit_color(discount_text)
                })
                
            except Exception as e:
                continue

        print(f"  [Result] МодаМакс: Успешно обработано: {len(results)}")
        return results

    except Exception as e:
        print(f"  [Error] МодаМакс: Ошибка CloudScraper: {e}")
        return []    


def get_discounts_econom():
    '''
    Функция получения действующих предложений от сети ЭкономСити
    '''
    url = 'https://secondhand.by/promos'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
            AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    print(f"  -> ЭкономСити: Скачиваем через requests...")
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # сбор списка адресов из price__cities
            address_list = []
            
            cities_container = soup.find('div', class_='price__cities')
            if not cities_container:
                print('Не найден блок адресов ЭкономСити')
                return []
            
            current_city = 'Минск' # значение по умолчанию
            
            # перебор всех элементов внутри блока адресов по очереди
            for element in cities_container.children:
                if element.name == 'div' and 'price__cities-title' in element.get('class', []):
                    # если попадается название города (заголовок), то запоминаем его
                    current_city = element.text.strip()
                
                elif element.name == 'a' and 'price__city' in element.get('class', []):
                    # если попадается адрес магазина, то берем его
                    street = element.text.strip()
                    # очистка адреса от лишних пробелов
                    street = ' '.join(street.split())
                    # формирую полный адрес
                    full_address = f'{current_city}, {street}'
                    address_list.append(full_address)
            print(f'  [Debug] ЭкономСити: найдено {len(address_list)} адресов.')
            # сбор списка скидок на сегодня
            discount_list = []
            
            # сегодняшние предложения находятся в блоке price__col--today
            today_col = soup.find('div', class_='price__col--today')
            
            if today_col:
                # собираю все ячейки в столбце сегодняшних предложений
                cells = today_col.find_all('div', class_='price__cell')
                for cell in cells:
                    text = cell.get_text(strip=True) # достает текст из вложенных тэгов и чистит его
                    # в ячейке может не быть текста, но быть пиктограмма с информацией
                    if not text:
                        img = cell.find('img')
                        if img and img.get('alt'):
                            text = img.get('alt')
                        else:
                            text = 'Предложений в магазине нет.'
                    
                    discount_list.append(text)
                print(f'  [Debug] ЭкономСити: найдено {len(discount_list)} строк с информацией о предложениях.')
            else:
                print('Колонка сегодняшнего дня ЭкономСити не найдена.')
                return []
            
            # объединение двух списков - адресов и скидок на сегодня
            # тут нужно предполагать, что оба списка - одинаковой длины
            # во избежание ошибки - принимаю за длину обоих списков длину кратчайшего
            limit = min(len(address_list), len(discount_list))
            
            for i in range(limit):
                address = address_list[i]
                discount_text = discount_list[i]
                
                results.append(
                    {
                        'shop_name': 'ЭкономСити',
                        'address': address,
                        'discount': discount_text,
                        'color': get_profit_color(discount_text)
                    }
                )
            print(f"  [Result] ЭкономСити: Успешно обработано: {len(results)}")
            return results
             
        else:
            print('Ошибка загрузки страницы ЭкономСити')
            return []
    except Exception as e:
        print(f'Глобальная ошибка при обработке ЭкономСити: {e}')
        return []        
    
def get_discounts():
    all_shops = []
    
    print("Парсим магазин 1 (МодаМакс)...")
    all_shops.extend(get_discounts_modamax())
    
    print("Парсим магазин 2 (ЭкономСити)...")
    all_shops.extend(get_discounts_econom())
    
    return all_shops