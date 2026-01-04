'''
Диаграмма Вороного — это способ разбиения плоскости на области, основанный на расстояниях до заданного множества точек (в нашем случае — магазинов).
Применение в ГИС: Определение зон обслуживания больниц, школ, пожарных частей и ритейла.
Как это работает: Строятся перпендикуляры к отрезкам, соединяющим соседние точки. Пересечения этих перпендикуляров образуют границы полигонов.
'''

import sqlite3
import numpy as np
from scipy.spatial import Voronoi
from shapely.geometry import Polygon, mapping, box
import geojson

def get_db_points():
    """
    Функция для импорта координат всех магазинов из Базы Данных
    """
    conn = sqlite3.connect('shops.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, shop_name, address, lat, lon, color FROM shops')
    rows = cursor.fetchall()
    
    conn.close()
    return rows

def generate_voronoi_geojson():
    """
    Функция для построения полигонов Вороного вокруг магазинов из базы данных.
    Возвращает FeatureCollection в формате GeoJSON.
    """
    rows = get_db_points()
    
    if not rows:
        print(f' [Warn] Из базы данных не вытянулись строки.')
        return None
    
    # метод Voronoi работает в плоскости и для точных карт нужно использовать проекции
    # я оперирую в рамках одного города - можно пренебречь искажениями и считать lat/lon координатами X/Y
    
    # подготовка данных - списка координат
    points = np.array([[row[3], row[4]] for row in rows])
    
    # диаграмма Вороного
    vor = Voronoi(points)
    
    # ограничивающая рамка bbox вокруг наших точек, чтобы полигоны не выходили за неё
    # границы рамки - мин/макс координаты магазинов -/+ отступ
    min_lat, min_lon = points.min(axis=0) - 0.05
    max_lat, max_lon = points.max(axis=0) + 0.05
    bbox = box(min_lat, min_lon, max_lat, max_lon)
    
    features = []
    
    # перебор полигонов = областей, созданных алгоритмом Voronoi
    # point_region - это индекс региона, соответствующего точке points[i]
    for i, region_index in enumerate(vor.point_region):
        region = vor.regions[region_index]
        
        # если область пустая или содержит вершину "в бесконечности" (-1), она игнорируется
        if not region or -1 in region:
            continue
        
        # координаты вершин областей
        polygon_coords = [vor.vertices[i] for i in region]
        
        # объект типа Polygon из библиотеки Shapely с координатами вершин областей
        clipped_poly = Polygon(polygon_coords)
        
        if clipped_poly.is_empty:
            continue
        
        # формирование GeoJSON
        # может быть путаница с координатами: GeoJSON ждёт (lon, lat), у меня (lat, lon)
        # mappint(clipped_poly) вернет структуру координат, её меняю местами
        swapped_coords = []
        if clipped_poly.geom_type == 'Polygon':
            exterior = [[p[1], p[0]] for p in list(clipped_poly.exterior.coords)]
            swapped_coords.append(exterior)
        
        feature = geojson.Feature(
            geometry=geojson.Polygon(swapped_coords),
            properties={
                'shop_name': rows[i][1],
                'address': rows[i][2],
                'color': rows[i][5]
            }
        )
        features.append(feature)
        
    return geojson.FeatureCollection(features)

