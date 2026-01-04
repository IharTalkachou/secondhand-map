from bs4 import BeautifulSoup
import re
import cloudscraper
from curl_cffi import requests as c_requests
import time

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
    
    print(f"  -> МодаМакс: Скачиваем через curl_cffi...")
    results = []
    
    # так как даже через curl_cffi соединение может отваливаться
    # буду перебирать по очереди разные браузеры, если будут ошибки
    browsers = ["chrome110", "safari15_5", "chrome100"]
    
    for browser in browsers:
        try:
            print(f'  [Try] Пробуем зайти на МодаМакс как {browser}')
            
            # простой запрос с использованием curl_cffi
            # impersonate=browser - скрипт имитирует работу одного из браузеров в списке browsers
            response = c_requests.get(url, impersonate=browser, timeout=30)
           
            if response.status_code != 200:
                print(f"  [Error] МодаМакс: Ошибка доступа: {response.status_code}")
                time.sleep(2)
                continue
                
            html_text = response.text
            
            # смотрю ответ - если скачалось слишком мало (10000 это не страница) - меняю браузер
            if len(html_text) < 10000:
                print(f"    [Warn] МодаМакс: Скачано мало - ({len(html_text)} байт). Повторяем...")
                time.sleep(2)
                continue
            
            # если скачено всё - успех
            print(f"  [Success] МодаМакс: Скачано байт: {len(html_text)}")
            
            # парсинг скаченного
            soup = BeautifulSoup(html_text, 'html.parser')
            
            # ищу строки скаченной таблицы
            rows = soup.find_all('div', class_='PriceTable__row')
            print(f"  [Debug] МодаМакс: Найдено строк PriceTable__row: {len(rows)}")
            
            # если строк нет - пробую с другим браузером
            if len(rows) == 0:
                print("    [Warn] Таблица не найдена в HTML.")
                continue
            
            # разбор распарсенных строк
            for row in rows:
                try:
                    # собираю адрес
                    addr_tag = row.find('a', class_='PriceTable__link')
                    if not addr_tag: continue
                    address = addr_tag.text.strip()
                    
                    # собираю цену/предложение
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
                    
                    # фильтр закрытых магазинов
                    if "не работает" in discount_text.lower() or discount_text == "-":
                        continue
                    
                    # склейка результатов
                    results.append({
                        "shop_name": "МодаМакс",
                        "address": address,
                        "discount": discount_text,
                        "color": get_profit_color(discount_text)
                    })
                    
                except Exception:
                    continue
            
            # если парсинг удался, выходим из цикла браузеров и возвращаем result
            print(f"  [Result] МодаМакс: Успешно обработано: {len(results)}")
            return results

        except Exception as e:
            print(f"  [Error] МодаМакс: Сбой при обработке curl_cffi с браузером {browser}: {e}")
            time.sleep(2)
    
    print('  [Fail] МодаМакс: Не удалось скачать данные после всех попыток.')
    return [] 


def get_discounts_econom():
    '''
    Функция получения действующих предложений от сети ЭкономСити
    '''
    url = 'https://secondhand.by/promos'
    
    print(f"  -> ЭкономСити: Скачиваем через cloudscraper...")
    results = []
    
    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # создаю справочник иконок ЭкономСити
            legend_map = {}
            
            legend_items = soup.find_all('div', class_='CalendarLegend__item')
            
            for item in legend_items:
                img = item.find('img')
                description_div = item.find('div', class_='CalendarLegend__item-title')
                
                if img and description_div:
                    src = img.get('src')
                    description = description_div.text.strip()
                    if src:
                        legend_map[src] = description
            
            print(f' [Debug] ЭкономСити: найдено {len(legend_map)} пиктограмм в легенде страницы.')
              
            # сбор списка адресов из price__cities
            address_list = []
            cities_container = soup.find('div', class_='price__cities')
            
            if not cities_container:
                print(f'  [Debug] ЭкономСити: Не найден блок адресов.')
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
                    # беру основной текст в ячейке
                    main_text = cell.get_text(strip=True, separator=' ') # достает текст из вложенных тэгов и чистит его
                    
                    # ищу иконки в ячейке
                    images_in_cell = cell.find_all('img')
                    additional_text = []
                    for img in images_in_cell:
                        src = img.get('src')
                        # если ссылка есть в справочнике иконок
                        if src in legend_map:
                            additional_text.append(legend_map[src])
                    
                    # склейка текста
                    if additional_text:
                        full_text = f"{main_text} {' '.join(additional_text)}"
                    else:
                        full_text = main_text
                    
                    # очистка от лишних пробелов
                    full_text = ' '.join(full_text.split())
                    
                    # на случай если так ничего не найдено в ячейке
                    if not full_text:
                        full_text = 'Предложений в магазине нет.'
                    
                    discount_list.append(full_text)
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