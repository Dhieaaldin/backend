import os
import math
from datetime import datetime
from typing import Dict, Any

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

# ------------------ Configuration ------------------
OPENWEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY')
OPENWEATHER_BASE_URL = 'https://api.openweathermap.org/data/2.5'
REQUESTS_TIMEOUT = 6  # seconds

if not OPENWEATHER_API_KEY:
    # Fail early in dev - remove or change in production if desired
    raise RuntimeError("Missing OPENWEATHER_API_KEY environment variable. Export it before running.")

app = Flask(__name__)
CORS(app)

# ------------------ Demo Data ------------------
DEMO_FARMS = {
    'farm_001': {
        'id': 'farm_001',
        'name': "Ahmed's Olive Grove",
        'owner': 'Ahmed Ben Salem',
        'location': {'lat': 35.8256, 'lon': 10.6369, 'city': 'Sousse'},
        'size_hectares': 2.0,
        'tree_count': 400,
        'tree_age_years': 15,
        'irrigation_system': 'drip',
        'soil_type': 'clay-loam',
        'last_irrigation': '2025-10-20',
        'ndvi_score': 0.45
    },
    'farm_002': {
        'id': 'farm_002',
        'name': "Fatima's Olive Grove",
        'owner': 'Fatima Trabelsi',
        'location': {'lat': 35.7753, 'lon': 10.8256, 'city': 'Monastir'},
        'size_hectares': 5.0,
        'tree_count': 1000,
        'tree_age_years': 20,
        'irrigation_system': 'drip',
        'soil_type': 'sandy-loam',
        'last_irrigation': '2025-10-22',
        'ndvi_score': 0.72
    },
    'farm_003': {
        'id': 'farm_003',
        'name': "Karim's Olive Grove",
        'owner': 'Karim Mansouri',
        'location': {'lat': 35.5047, 'lon': 11.0586, 'city': 'Mahdia'},
        'size_hectares': 3.0,
        'tree_count': 600,
        'tree_age_years': 12,
        'irrigation_system': 'sprinkler',
        'soil_type': 'loam',
        'last_irrigation': '2025-10-18',
        'ndvi_score': 0.38
    }
}

# ------------------ Helper Functions ------------------


def fetch_weather_data(lat: float, lon: float) -> Dict[str, Any]:
    """
    Fetch current weather and forecast using OpenWeather.
    Returns a dict with 'success' key and 'current' and 'forecast' if successful.
    """
    try:
        # Current weather
        current_url = f"{OPENWEATHER_BASE_URL}/weather"
        current_params = {
            'lat': lat,
            'lon': lon,
            'appid': OPENWEATHER_API_KEY,
            'units': 'metric'
        }
        current_resp = requests.get(current_url, params=current_params, timeout=REQUESTS_TIMEOUT)
        current_resp.raise_for_status()
        current_data = current_resp.json()

        # 5-day forecast (3h steps)
        forecast_url = f"{OPENWEATHER_BASE_URL}/forecast"
        forecast_params = {
            'lat': lat,
            'lon': lon,
            'appid': OPENWEATHER_API_KEY,
            'units': 'metric',
            'cnt': 40
        }
        forecast_resp = requests.get(forecast_url, params=forecast_params, timeout=REQUESTS_TIMEOUT)
        forecast_resp.raise_for_status()
        forecast_data = forecast_resp.json()

        # Process forecast into daily-ish entries (every 8 steps ≈ 24h)
        daily_forecast = []
        items = forecast_data.get('list', [])
        for i in range(0, len(items), 8):
            item = items[i]
            daily_forecast.append({
                'date': item['dt_txt'].split()[0],
                'temp_max': item['main'].get('temp_max', item['main'].get('temp')),
                'temp_min': item['main'].get('temp_min', item['main'].get('temp')),
                'humidity': item['main'].get('humidity'),
                'wind_speed': item.get('wind', {}).get('speed', 0.0),
                'weather': item.get('weather', [{}])[0].get('main', ''),
                'rain_probability': item.get('pop', 0) * 100
            })

        result = {
            'success': True,
            'current': {
                'temperature': current_data['main'].get('temp'),
                'humidity': current_data['main'].get('humidity'),
                'wind_speed': current_data.get('wind', {}).get('speed', 0.0),
                'weather': current_data.get('weather', [{}])[0].get('main', ''),
                'description': current_data.get('weather', [{}])[0].get('description', '')
            },
            'forecast': daily_forecast[:7]
        }
        return result

    except Exception as e:
        # Return mocked fallback but indicate error
        return {
            'success': False,
            'error': str(e),
            'current': {
                'temperature': 28,
                'humidity': 65,
                'wind_speed': 3.5,
                'weather': 'Clear',
                'description': 'clear sky'
            },
            'forecast': [
                {'date': '2025-10-25', 'temp_max': 30, 'temp_min': 20, 'humidity': 60, 'wind_speed': 3.2, 'weather': 'Clear', 'rain_probability': 5},
                {'date': '2025-10-26', 'temp_max': 29, 'temp_min': 19, 'humidity': 65, 'wind_speed': 3.5, 'weather': 'Clear', 'rain_probability': 10},
                {'date': '2025-10-27', 'temp_max': 27, 'temp_min': 18, 'humidity': 70, 'wind_speed': 4.0, 'weather': 'Clouds', 'rain_probability': 30}
            ]
        }


def calculate_et0(temp_max: float, temp_min: float, humidity: float, wind_speed: float, latitude: float, day_of_year: int) -> float:
    """
    Calculate reference evapotranspiration (ET0) using a simplified Penman-Monteith.
    Returns ET0 in mm/day (non-negative).
    """
    # Mean temperature (°C)
    temp_mean = (temp_max + temp_min) / 2.0

    # Solar geometry
    lat_rad = math.radians(latitude)
    solar_declination = 0.409 * math.sin((2 * math.pi / 365) * day_of_year - 1.39)
    sunset_angle = math.acos(max(-1.0, min(1.0, -math.tan(lat_rad) * math.tan(solar_declination))))

    # Extraterrestrial radiation (Ra) [MJ m-2 day-1] (simplified)
    dr = 1 + 0.033 * math.cos(2 * math.pi * day_of_year / 365)
    ra = 37.6 * dr * (sunset_angle * math.sin(lat_rad) * math.sin(solar_declination) +
                      math.cos(lat_rad) * math.cos(solar_declination) * math.sin(sunset_angle))

    # Net radiation (simplified) - ensure non-negative
    rs = (0.25 + 0.5) * ra  # assume moderate sunshine fraction
    rn = max(0.0, 0.77 * rs - 0.9)

    # Saturation vapor pressures
    e_tmax = 0.6108 * math.exp((17.27 * temp_max) / (temp_max + 237.3))
    e_tmin = 0.6108 * math.exp((17.27 * temp_min) / (temp_min + 237.3))
    es = (e_tmax + e_tmin) / 2.0

    # Actual vapor pressure
    ea = es * (humidity / 100.0)

    vpd = max(0.0, es - ea)  # vapor pressure deficit

    # Wind speed adjustment to 2 m (FAO-56 approximation)
    z = 10.0  # assume measurement height (m)
    denom = math.log(67.8 * z + 5.42)
    u2 = wind_speed * (4.87 / denom) if denom > 0 else wind_speed

    # Simplified Penman-Monteith (FAO-like) - constants gamma and delta omitted for simplicity,
    # use a practical approximation:
    # ET0 = (0.408 * Rn + (900/(T+273)) * u2 * vpd) / (T + 273)?? => FAO uses: (0.408*delta*(Rn-G) + gamma*900/(T+273)*u2*(es-ea)) / (delta + gamma*(1+0.34*u2))
    # For demo we use the commonly used approximate form:
    try:
        et0 = (0.408 * rn + (900.0 / (temp_mean + 273.0)) * u2 * vpd) / (1.0 + 0.34 * u2)
    except Exception:
        et0 = 0.0

    return max(0.0, et0)


def calculate_crop_coefficient(ndvi_score: float, growth_stage: str = 'mid') -> float:
    """
    Calculate crop coefficient (Kc) based on NDVI and growth stage.
    Clamped to a reasonable range to avoid unrealistic values.
    """
    base_kc = {'initial': 0.50, 'mid': 0.65, 'late': 0.60}
    if ndvi_score < 0.3:
        adjustment = 0.15
    elif ndvi_score < 0.5:
        adjustment = 0.10
    elif ndvi_score < 0.7:
        adjustment = 0.05
    else:
        adjustment = 0.0

    kc = base_kc.get(growth_stage, 0.65) + adjustment
    # clamp Kc to [0.4, 0.85]
    kc = min(max(kc, 0.4), 0.85)
    return kc


def calculate_water_savings(traditional_amount: float, smart_amount: float) -> Dict[str, float]:
    """
    Calculate water and cost savings.
    Inputs are in cubic meters (m3). Cost baseline: 0.5 TND per m3 (approx).
    """
    if traditional_amount <= 0 or smart_amount < 0:
        return {
            'water_saved_liters': 0.0,
            'water_saved_cubic_meters': 0.0,
            'percentage_saved': 0.0,
            'cost_saved_tnd': 0.0,
            'cost_saved_usd': 0.0
        }

    water_saved_m3 = max(0.0, traditional_amount - smart_amount)
    water_saved_liters = water_saved_m3 * 1000.0
    percentage_saved = (water_saved_m3 / traditional_amount) * 100.0 if traditional_amount > 0 else 0.0

    # Cost savings (approx 0.5 TND per m3)
    cost_saved_tnd = water_saved_m3 * 0.5
    cost_saved_usd = cost_saved_tnd * 0.32  # rough conversion

    return {
        'water_saved_liters': round(water_saved_liters, 2),
        'water_saved_cubic_meters': round(water_saved_m3, 2),
        'percentage_saved': round(percentage_saved, 2),
        'cost_saved_tnd': round(cost_saved_tnd, 2),
        'cost_saved_usd': round(cost_saved_usd, 2)
    }

# ------------------ API Endpoints ------------------


@app.route('/')
def home():
    return jsonify({
        'message': 'Smart Olive Irrigation API',
        'version': '1.1-fixed',
        'endpoints': {
            'farms': '/api/farms',
            'weather': '/api/weather/<lat>/<lon>',
            'irrigation': '/api/calculate-irrigation',
            'ndvi': '/api/farms/<farm_id>/ndvi',
            'savings': '/api/farms/<farm_id>/savings'
        }
    })


@app.route('/api/farms', methods=['GET'])
def get_farms():
    return jsonify({'success': True, 'count': len(DEMO_FARMS), 'farms': list(DEMO_FARMS.values())})


@app.route('/api/farms/<farm_id>', methods=['GET'])
def get_farm(farm_id):
    farm = DEMO_FARMS.get(farm_id)
    if not farm:
        return jsonify({'success': False, 'error': 'Farm not found'}), 404
    return jsonify({'success': True, 'farm': farm})


@app.route('/api/weather/<lat>/<lon>', methods=['GET'])
def get_weather_route(lat, lon):
    """
    Public route - returns weather data for lat/lon using fetch_weather_data
    """
    try:
        latf = float(lat)
        lonf = float(lon)
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid lat/lon'}), 400

    data = fetch_weather_data(latf, lonf)
    return jsonify(data)


@app.route('/api/calculate-irrigation', methods=['POST'])
def calculate_irrigation():
    """
    Main endpoint: calculate irrigation need based on farm or provided params.
    Expects JSON with optional farm_id or direct params:
    {
        "farm_id": "farm_001",
        "latitude": 35.8,
        "longitude": 10.6,
        "size_hectares": 2.0,
        "tree_count": 400,
        "ndvi_score": 0.5
    }
    """
    data = request.get_json() or {}

    # Extract input values (fallback to defaults or farm data)
    farm_id = data.get('farm_id')
    lat = data.get('latitude')
    lon = data.get('longitude')
    size_hectares = data.get('size_hectares')
    tree_count = data.get('tree_count')
    ndvi_score = data.get('ndvi_score')

    # If farm_id provided, override with DEMO_FARMS values
    if farm_id and farm_id in DEMO_FARMS:
        farm = DEMO_FARMS[farm_id]
        lat = farm['location']['lat']
        lon = farm['location']['lon']
        size_hectares = farm['size_hectares']
        tree_count = farm['tree_count']
        ndvi_score = farm['ndvi_score']
    else:
        # cast or default
        try:
            lat = float(lat) if lat is not None else 35.8
            lon = float(lon) if lon is not None else 10.6
            size_hectares = float(size_hectares) if size_hectares is not None else 2.0
            tree_count = int(tree_count) if tree_count is not None else 400
            ndvi_score = float(ndvi_score) if ndvi_score is not None else 0.5
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Invalid input parameter types'}), 400

    # Fetch weather using helper (not calling route directly)
    weather = fetch_weather_data(lat, lon)
    weather_success = weather.get('success', False)

    # Use returned data (if failed, fetch_weather_data returns fallback with success=False)
    current = weather.get('current', {})
    forecast = weather.get('forecast', [])[:3]  # next 3 days

    # If no forecast entries, create a simple fallback
    if not forecast:
        forecast = [
            {'temp_max': current.get('temperature', 28), 'temp_min': current.get('temperature', 20),
             'humidity': current.get('humidity', 65), 'wind_speed': current.get('wind_speed', 3.5),
             'weather': current.get('weather', 'Clear'), 'rain_probability': 0}
        ]

    # Compute ET0 over next 3 days
    total_et0 = 0.0
    day_of_year = datetime.now().timetuple().tm_yday
    for day in forecast:
        et0 = calculate_et0(
            temp_max=day.get('temp_max', 28),
            temp_min=day.get('temp_min', 18),
            humidity=day.get('humidity', 65),
            wind_speed=day.get('wind_speed', 3.5),
            latitude=lat,
            day_of_year=day_of_year
        )
        total_et0 += et0
        day_of_year += 1

    # Crop water requirement
    kc = calculate_crop_coefficient(ndvi_score, 'mid')
    etc = total_et0 * kc  # mm over 3 days

    # Rough rainfall adjustment (estimate: probability*rain_depth (assume 5 mm if it rains))
    expected_rain = sum((d.get('rain_probability', 0) / 100.0) * 5.0 for d in forecast)
    net_irrigation_mm = max(0.0, etc - expected_rain)

    # Convert mm to volume
    area_m2 = max(0.0, size_hectares) * 10000.0
    irrigation_m3 = (net_irrigation_mm / 1000.0) * area_m2
    irrigation_liters = irrigation_m3 * 1000.0
    liters_per_tree = irrigation_liters / tree_count if tree_count > 0 else 0.0

    # Traditional method (assumes 50% more water usage - baseline)
    traditional_m3 = irrigation_m3 * 1.5

    # Savings calculation
    savings = calculate_water_savings(traditional_m3, irrigation_m3)

    # Irrigation duration (drip system: assume 4 liters/hour per tree)
    hours_per_tree = liters_per_tree / 4.0 if liters_per_tree > 0 else 0.0

    # Health status
    if ndvi_score < 0.3:
        health_status = 'Critical - High Stress'
        urgency = 'urgent'
        message = '🚨 Severe drought stress detected. Immediate irrigation recommended.'
    elif ndvi_score < 0.5:
        health_status = 'Moderate Stress'
        urgency = 'high'
        message = '⚠️ Trees showing stress. Irrigation recommended soon.'
    elif ndvi_score < 0.7:
        health_status = 'Healthy'
        urgency = 'normal'
        message = '✓ Trees are healthy. Follow recommended schedule.'
    else:
        health_status = 'Excellent'
        urgency = 'low'
        message = '✓ Trees in excellent condition.'

    response = {
        'success': True,
        'recommendation': {
            'irrigation_needed_mm': round(net_irrigation_mm, 2),
            'irrigation_needed_m3': round(irrigation_m3, 3),
            'irrigation_needed_liters': round(irrigation_liters, 2),
            'liters_per_tree': round(liters_per_tree, 2),
            'duration_hours_per_tree': round(hours_per_tree, 2),
            'schedule': 'Next 3 days',
            'urgency': urgency,
            'message': message
        },
        'tree_health': {
            'ndvi_score': round(ndvi_score, 3),
            'status': health_status,
            'kc_coefficient': round(kc, 3)
        },
        'weather_analysis': {
            'total_et0_mm': round(total_et0, 2),
            'expected_rain_mm': round(expected_rain, 2),
            'current_temp': current.get('temperature'),
            'forecast_summary': " → ".join(d.get('weather', '') for d in (forecast + [{}])[:3])
        },
        'savings': savings,
        'comparison': {
            'traditional_method_m3': round(traditional_m3, 3),
            'smart_method_m3': round(irrigation_m3, 3),
            'efficiency_improvement': f"{savings['percentage_saved']}%"
        },
        'weather_fetch_success': weather_success
    }

    # If weather fetch failed, include the error message for debugging
    if not weather_success:
        response['weather_error'] = weather.get('error', 'Weather fetch failed')

    return jsonify(response)


@app.route('/api/farms/<farm_id>/ndvi', methods=['GET'])
def get_ndvi(farm_id):
    farm = DEMO_FARMS.get(farm_id)
    if not farm:
        return jsonify({'success': False, 'error': 'Farm not found'}), 404

    ndvi_score = farm['ndvi_score']
    zones = []
    if ndvi_score < 0.4:
        zones = [
            {'zone': 'North', 'ndvi': 0.35, 'status': 'Stressed', 'area_pct': 40},
            {'zone': 'Center', 'ndvi': 0.40, 'status': 'Moderate', 'area_pct': 35},
            {'zone': 'South', 'ndvi': 0.45, 'status': 'Moderate', 'area_pct': 25}
        ]
    elif ndvi_score < 0.6:
        zones = [
            {'zone': 'North', 'ndvi': 0.50, 'status': 'Moderate', 'area_pct': 30},
            {'zone': 'Center', 'ndvi': 0.55, 'status': 'Healthy', 'area_pct': 45},
            {'zone': 'South', 'ndvi': 0.48, 'status': 'Moderate', 'area_pct': 25}
        ]
    else:
        zones = [
            {'zone': 'North', 'ndvi': 0.70, 'status': 'Healthy', 'area_pct': 40},
            {'zone': 'Center', 'ndvi': 0.75, 'status': 'Excellent', 'area_pct': 40},
            {'zone': 'South', 'ndvi': 0.68, 'status': 'Healthy', 'area_pct': 20}
        ]

    return jsonify({
        'success': True,
        'farm_id': farm_id,
        'overall_ndvi': ndvi_score,
        'acquisition_date': '2025-10-22',
        'satellite': 'Sentinel-2',
        'zones': zones,
        'recommendations': [
            'Focus irrigation on stressed zones' if ndvi_score < 0.5 else 'Maintain current irrigation schedule',
            'Monitor North zone closely' if any(z['status'] == 'Stressed' for z in zones) else 'All zones performing well'
        ]
    })


@app.route('/api/farms/<farm_id>/savings', methods=['GET'])
def get_savings(farm_id):
    farm = DEMO_FARMS.get(farm_id)
    if not farm:
        return jsonify({'success': False, 'error': 'Farm not found'}), 404

    size = farm['size_hectares']
    traditional_usage = max(0.0, size) * 5000.0  # baseline
    smart_usage = max(0.0, size) * 3200.0
    savings = calculate_water_savings(traditional_usage, smart_usage)

    return jsonify({
        'success': True,
        'farm_id': farm_id,
        'period': 'Current Season (Oct 2024 - Oct 2025)',
        'traditional_usage_m3': round(traditional_usage, 2),
        'smart_usage_m3': round(smart_usage, 2),
        'savings': savings,
        'environmental_impact': {
            'aquifer_preservation_m3': savings['water_saved_cubic_meters'],
            'co2_saved_kg': round(savings['water_saved_cubic_meters'] * 0.5, 2),
            'trees_equivalent': round(savings['water_saved_cubic_meters'] / 100, 0)
        },
        'monthly_breakdown': [
            {'month': 'Nov 2024', 'saved_m3': round(traditional_usage * 0.08, 1), 'saved_tnd': round(traditional_usage * 0.08 * 0.5, 2)},
            {'month': 'Dec 2024', 'saved_m3': round(traditional_usage * 0.06, 1), 'saved_tnd': round(traditional_usage * 0.06 * 0.5, 2)},
            {'month': 'Jan 2025', 'saved_m3': round(traditional_usage * 0.05, 1), 'saved_tnd': round(traditional_usage * 0.05 * 0.5, 2)}
        ]
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # Note: set debug=False in production
    app.run(host='0.0.0.0', port=port, debug=True)
