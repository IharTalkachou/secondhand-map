import requests
from bs4 import BeautifulSoup

def get_discounts_modamax():
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
                            'address': address,
                            'discount': discount_text
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

if __name__ == '__main__':
    print(get_discounts_modamax())