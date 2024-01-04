from fastapi import FastAPI
from typing import List
from haversine import haversine
import json

app = FastAPI()

# Function to load data from JSON file
def load_station_data(file_path):
    data = []
    with open(file_path, 'r') as file:
        for line in file:
            try:
                json_data = json.loads(line)
                data.append(json_data)
            except json.JSONDecodeError:
                continue
    return data

# Load your JSON data here
stations = load_station_data("output_priority.json")

@app.get("/stations")
async def get_stations(lat: float, lon: float, radius: float, capacity: int) -> List[dict]:
    user_location = (lat, lon)
    stations = load_station_data("output_priority.json")
    def is_within_radius(station, max_radius):
        if 'lat' in station and 'lon' in station:
            station_location = (station['lat'], station['lon'])
            return haversine(user_location, station_location, unit='mi') <= max_radius
        else:
            return False


    nearby_stations = [
        station for station in stations
        if is_within_radius(station, radius) 
    ]

    nearby_stations.sort(key=lambda x: x.get('maintenance_priority', 0) if x.get('maintenance_priority') is not None else 0, reverse=True)
    
    return nearby_stations[:capacity]

@app.get("/stations/high-traffic")
async def get_high_traffic_stations(lat: float, lon: float, radius: float, capacity: int) -> List[dict]:
    user_location = (lat, lon)
    stations = load_station_data("output_priority.json")
    def is_within_radius(station, max_radius):
        if 'lat' in station and 'lon' in station:
            station_location = (station['lat'], station['lon'])
            return haversine(user_location, station_location, unit='mi') <= max_radius
        else:
            return False

    # Filter stations within the radius
    nearby_stations = [station for station in stations if is_within_radius(station, radius)]

    # Assuming each station has a 'traffic' key that stores the traffic information
    # Sort the stations by traffic in decreasing order
    high_traffic_stations = sorted(nearby_stations, key=lambda x: x.get('predicted_traffic', 0), reverse=True)
    
    return high_traffic_stations[:capacity]


@app.get("/stations/by-distance")
async def get_stations_by_distance(lat: float, lon: float, radius: float, capacity: int) -> List[dict]:
    user_location = (lat, lon)
    stations = load_station_data("output_priority.json")
    def distance_from_user(station):
        station_location = (station['lat'], station['lon'])
        return haversine(user_location, station_location, unit='mi')

    def is_within_radius(station, max_radius):
        return distance_from_user(station) <= max_radius

    # Filter stations within the radius
    nearby_stations = [station for station in stations if is_within_radius(station, radius)]

    # Sort stations by distance from the user location
    nearby_stations.sort(key=distance_from_user)

    return nearby_stations[:capacity]

@app.get("/stations/combined-scoring")
async def get_stations_combined_scoring(lat: float, lon: float, radius: float, capacity: int) -> List[dict]:
    user_location = (lat, lon)
    stations = load_station_data("output_priority.json")
    def distance_from_user(station):
        station_location = (station['lat'], station['lon'])
        return haversine(user_location, station_location, unit='mi')

    def combined_score(station):
        # Assuming max values for normalization, adjust these based on your data
        max_distance = radius  
        max_priority = max(stations, key=lambda x: x['maintenance_priority'])['maintenance_priority'] 
        max_traffic = max(stations, key=lambda x: x['predicted_traffic'])['predicted_traffic'] 

        # Normalize values (invert distance as closer is better)
        normalized_distance = (max_distance - distance_from_user(station)) / max_distance
        normalized_priority = station.get('maintenance_priority', 0) / max_priority
        normalized_traffic = station.get('traffic', 0) / max_traffic

        # You can adjust weights here based on what factor you want to prioritize
        return normalized_distance + normalized_priority + normalized_traffic

    nearby_stations = [station for station in stations if distance_from_user(station) <= radius]

    # Sort by combined score in descending order
    nearby_stations.sort(key=combined_score, reverse=True)

    return nearby_stations[:capacity]

@app.get("/stations/discounts")
async def get_stations_with_discounts(lat: float, lon: float, radius: float, capacity: int) -> List[dict]:
    user_location = (lat, lon)
    stations = load_station_data("output_priority.json")
    def calculate_discount(station):
        predicted_traffic = station.get('predicted_traffic', 0)
        number_of_vehicles_available = station['num_vehicles_available']

        # Avoid division by zero
        if number_of_vehicles_available == 0:
            number_of_vehicles_available = 0.05

        if predicted_traffic > number_of_vehicles_available:
            discount = (number_of_vehicles_available / predicted_traffic) * 100
        else:
            discount = (predicted_traffic / number_of_vehicles_available) * 100

        # Increase discount if availability is very low
        if number_of_vehicles_available < 0.1 * station['capacity']:
            discount += 5

        max_possible_discount = 100 + 5  # 100% plus potential 5% increase
        scaled_discount = (discount / max_possible_discount) * 20

        return min(scaled_discount, 20)
          # Ensure discount does not exceed 20%

    def is_within_radius(station, max_radius):
        station_location = (station['lat'], station['lon'])
        return haversine(user_location, station_location, unit='mi') <= max_radius

    # Filter for stations within the radius and have more than 0 vehicles available
    nearby_stations = [
        {**station, 'discount': calculate_discount(station)}
        for station in stations
        if is_within_radius(station, radius) and station['num_vehicles_available'] > 0
    ]

    # Sort stations by discount in descending order
    nearby_stations.sort(key=lambda x: x['discount'], reverse=True)

    return nearby_stations[:capacity]