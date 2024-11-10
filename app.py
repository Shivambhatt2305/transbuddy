import os
import folium
import pandas as pd
import numpy as np
import aiohttp
import asyncio
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename

app = Flask(__name__)  # Corrected initialization
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'csv'}
app.secret_key = 'your_randomly_generated_secret_key'

# Set your TomTom API key here
TOMTOM_API_KEY = 'WPglpwBsq3RAlGQqJ8t4TkpRihGrspCI'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def load_route_data(filepath):
    data = pd.read_csv(filepath)
    if 'latitude' in data.columns:
        data[['latitude', 'longitude']] = data['latitude'].str.split(',', expand=True)
        data['latitude'] = data['latitude'].astype(float)
        data['longitude'] = data['longitude'].astype(float)

    bus_routes = {}
    for bus_id in data['bus_id'].unique():
        bus_routes[bus_id] = {
            "route": data[data['bus_id'] == bus_id][['stop_name', 'latitude', 'longitude']].to_dict('records')
        }
    return bus_routes

async def get_tomtom_route(session, start_coords, end_coords):
    url = f"https://api.tomtom.com/routing/1/calculateRoute/{start_coords[0]},{start_coords[1]}:{end_coords[0]},{end_coords[1]}/json"
    params = {
        'key': TOMTOM_API_KEY,
        'traffic': 'false'
    }
    async with session.get(url, params=params) as response:
        route = await response.json()
        if route.get("routes"):
            geometry = route["routes"][0]["legs"][0]["points"]
            return [(point['latitude'], point['longitude']) for point in geometry]
        return []

async def fetch_routes_concurrently(route_points):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(len(route_points) - 1):
            start_coords = [route_points[i]['latitude'], route_points[i]['longitude']]
            end_coords = [route_points[i+1]['latitude'], route_points[i+1]['longitude']]
            tasks.append(get_tomtom_route(session, start_coords, end_coords))
        return await asyncio.gather(*tasks)

@app.route('/', methods=['GET', 'POST'])
def index():
    bus_routes = {}
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)

        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Load bus routes from CSV
            bus_routes = load_route_data(filepath)
            session['bus_routes'] = bus_routes  # Save in session for persistence
        else:
            return redirect(request.url)

    return render_template('index.html', bus_routes=session.get('bus_routes', {}))

@app.route('/display_route', methods=['POST'])
def display_route():
    selected_bus = request.form.get('bus')
    bus_routes = session.get('bus_routes', {})

    if selected_bus not in bus_routes:
        return redirect(url_for('index'))

    route_points = bus_routes[selected_bus]['route']

    # Initialize the map at the center of the first stop
    map_center = [route_points[0]['latitude'], route_points[0]['longitude']]
    m = folium.Map(location=map_center, zoom_start=12)

    # Fetch the exact route asynchronously
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    route_paths = loop.run_until_complete(fetch_routes_concurrently(route_points))

    # Add the route to the map
    for path in route_paths:
        folium.PolyLine(path, color="blue", weight=2.5, opacity=1).add_to(m)

    # Add bus stops as markers
    for stop in route_points:
        folium.Marker([stop['latitude'], stop['longitude']], popup=stop['stop_name']).add_to(m)

    return render_template('index.html', bus_routes=bus_routes, map=m._repr_html_())

if __name__ == '__main__':  # Corrected initialization
    app.run(debug=True)
