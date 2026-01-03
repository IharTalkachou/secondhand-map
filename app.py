from flask import Flask, jsonify, render_template
import sqlite3

app = Flask(__name__)

def get_shops_from_db():
    conn = sqlite3.connect('shops.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM shops')
    rows = cursor.fetchall()
    conn.close()
    return rows

@app.route('/api/shops')
def api_shops():
    rows = get_shops_from_db()
    
    features = []
    for row in rows:
        feature = {
            'type': 'Feature',
            'properties': {
                'address': row['address'],
                'discount': row['discount']
            },
            'geometry': {
                'type': 'Point',
                'coordinates': [row['lon'], row['lat']]
            }
        }
        features.append(feature)
    
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    return jsonify(geojson)

@app.route('/')
def index():
    return render_template('map.html')

if __name__ == '__main__':
    app.run(debug=True)