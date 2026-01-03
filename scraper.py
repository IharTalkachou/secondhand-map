import requests
from bs4 import BeautifulSoup
import re

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
    url = 'https://modamax.by/price/minsk'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            rows = soup.find_all('div', class_='PriceTable__row')
            results = []
            
            for row in rows:
                try:
                    addr_tag = row.find('a', class_='PriceTable__link')
                    if not addr_tag: continue
                    address = addr_tag.text.strip()
                    
                    today_col = row.find('div', class_='PriceTable__col--today')
                    discount_text = 'Нет данных'
                    
                    if today_col:
                        amount_div = today_col.find('div', class_='PriceTable__amount-numbers')
                        
                        if amount_div:
                            rub = amount_div.contents[0].strip()
                            
                            coins_span = amount_div.find('span', class_='PriceTable__amount-coins')
                            coins = coins_span.text.strip() if coins_span else '00'
                            
                            measure_span = amount_div.find('span', class_='PriceTable__amount-text')
                            measure = measure_span.text.strip() if measure_span else 'вещь или кг'
                            
                            discount_text = f'{rub}.{coins} руб{measure}'
                            
                            icon = today_col.find('img')
                            if icon and icon.get('alt'):
                                discount_text += f" ({icon.get('alt')})"
                    
                    results.append(
                        {
                            'shop_name': 'МодаМакс',
                            'address': address,
                            'discount': discount_text,
                            'color': get_profit_color(discount_text)
                        }
                    )
                except Exception as e:
                    print(f'Ошибка при разборе строки {e}')
                    continue
            
            return results
        else:
            print('Ошибка загрузки страницы')
            return []
            
    except Exception as e:
        print(f'Глобальная ошибка {e}')
        return []

def get_discounts_econom():
    '''
    Функция получения действующих предложений от сети ЭкономСити
    '''
    return [
        {
            "shop_name": "ЭкономСити",
            "address": "Минск, ул.Романовская Слобода, 12",
            "discount": "-70%",
            "color": get_profit_color("-70%")
        },
        {
            "shop_name": "ЭкономСити",
            "address": "Минск, пр-т Рокоссовского, 114",
            "discount": "2 руб/вещь",
            "color": get_profit_color("2 руб/вещь")
        }
    ]

def get_discounts():
    all_shops = []
    
    print("Парсим магазин 1...")
    all_shops.extend(get_discounts_modamax())
    
    print("Парсим магазин 2...")
    all_shops.extend(get_discounts_econom())
    
    return all_shops