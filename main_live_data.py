import math
import datetime
import requests
import ee

# =====================================================
#  INITIALIZATION
# =====================================================

# 🔑 Set your API keys here
OPENWEATHER_API_KEY = "YOUR_OPENWEATHER_KEY"

# Initialize Google Earth Engine
try:
    ee.Initialize()
    GEE_AVAILABLE = True
except Exception:
    GEE_AVAILABLE = False
    print("⚠️ Google Earth Engine not initialized. NDVI will use fallback (0.6).")

# =====================================================
#  1️⃣ WEATHER FETCH (OpenWeather)
# =====================================================
def get_weather(lat, lon):
    """Fetch real-time weather data from OpenWeather"""
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
    r = requests.get(url)
    data = r.json()

    temp_max = data["main"]["temp_max"]
    temp_min = data["main"]["temp_min"]
    humidity = data["main"]["humidity"]
    wind_speed = data["wind"]["speed"]

    return {
        "temp_max": temp_max,
        "temp_min": temp_min,
        "humidity": humidity,
        "wind_speed": wind_speed,
        "latitude": lat,
        "day_of_year": datetime.date.today().timetuple().tm_yday
    }

# =====================================================
#  2️⃣ NDVI FETCH (Google Earth Engine)
# =====================================================
def get_ndvi_from_gee(lat, lon, start_date, end_date):
    """Fetch NDVI from Sentinel-2 imagery using Google Earth Engine"""
    point = ee.Geometry.Point([lon, lat])

    collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                  .filterBounds(point)
                  .filterDate(start_date, end_date)
                  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)))

    ndvi_collection = collection.map(lambda image:
        image.addBands(image.normalizedDifference(['B8', 'B4']).rename('NDVI'))
    )

    ndvi_image = ndvi_collection.mean().select('NDVI')

    ndvi_value = ndvi_image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=point,
        scale=10
    ).get('NDVI').getInfo()

    if ndvi_value is None:
        ndvi_value = 0.5
    return round(ndvi_value, 2)


def get_real_ndvi(lat, lon):
    """Get NDVI using GEE or fallback"""
    today = datetime.date.today()
    start = today - datetime.timedelta(days=10)
    end = today

    if GEE_AVAILABLE:
        try:
            return get_ndvi_from_gee(lat, lon, str(start), str(end))
        except Exception as e:
            print("⚠️ NDVI fetch failed:", e)
            return 0.6
    else:
        return 0.6

# =====================================================
#  3️⃣ CORE CALCULATIONS
# =====================================================
def calculate_et0(temp_max, temp_min, humidity, wind_speed, latitude, day_of_year):
    """Calculate reference evapotranspiration (ET0) using simplified Penman-Monteith"""
    temp_mean = (temp_max + temp_min) / 2
    lat_rad = math.radians(latitude)
    solar_declination = 0.409 * math.sin((2 * math.pi / 365) * day_of_year - 1.39)
    sunset_angle = math.acos(-math.tan(lat_rad) * math.tan(solar_declination))
    dr = 1 + 0.033 * math.cos(2 * math.pi * day_of_year / 365)
    ra = 37.6 * dr * (sunset_angle * math.sin(lat_rad) * math.sin(solar_declination) +
                      math.cos(lat_rad) * math.cos(solar_declination) * math.sin(sunset_angle))
    rs = (0.25 + 0.5 * 1) * ra
    rn = 0.77 * rs - 0.9
    e_tmax = 0.6108 * math.exp((17.27 * temp_max) / (temp_max + 237.3))
    e_tmin = 0.6108 * math.exp((17.27 * temp_min) / (temp_min + 237.3))
    es = (e_tmax + e_tmin) / 2
    ea = es * (humidity / 100)
    vpd = es - ea
    u2 = wind_speed * (4.87 / math.log(67.8 * 10 - 5.42))
    et0 = (0.408 * rn + 900 * (temp_mean + 273) * u2 * vpd / (temp_mean + 273)) / (1 + 0.34 * u2)
    return max(0, et0)

def calculate_crop_coefficient(ndvi_score, growth_stage='mid'):
    """Calculate crop coefficient based on NDVI and growth stage"""
    base_kc = {
        'initial': 0.50,
        'mid': 0.65,
        'late': 0.60
    }

    if ndvi_score < 0.3:
        adjustment = 0.15
    elif ndvi_score < 0.5:
        adjustment = 0.10
    elif ndvi_score < 0.7:
        adjustment = 0.05
    else:
        adjustment = 0.0

    return base_kc.get(growth_stage, 0.65) + adjustment

def calculate_water_savings(traditional_amount, smart_amount):
    """Calculate water and cost savings"""
    water_saved_liters = (traditional_amount - smart_amount) * 1000
    percentage_saved = ((traditional_amount - smart_amount) / traditional_amount) * 100
    cost_saved_tnd = water_saved_liters * 0.0005
    return {
        'water_saved_liters': round(water_saved_liters, 2),
        'water_saved_cubic_meters': round(traditional_amount - smart_amount, 2),
        'percentage_saved': round(percentage_saved, 2),
        'cost_saved_tnd': round(cost_saved_tnd, 2),
        'cost_saved_usd': round(cost_saved_tnd * 0.32, 2)
    }

# =====================================================
#  4️⃣ MAIN LOGIC
# =====================================================
def run_irrigation_ai(lat, lon, traditional_amount=5.0, growth_stage='mid'):
    weather = get_weather(lat, lon)
    ndvi = get_real_ndvi(lat, lon)
    kc = calculate_crop_coefficient(ndvi, growth_stage)
    et0 = calculate_et0(**weather)
    smart_irrigation = et0 * kc * 0.1  # simplified conversion
    savings = calculate_water_savings(traditional_amount, smart_irrigation)

    print("\n🌍 Smart Irrigation AI Results")
    print("-----------------------------")
    print(f"📍 Location: ({lat}, {lon})")
    print(f"🌿 NDVI: {ndvi}")
    print(f"☀️ ET₀: {et0:.2f} mm/day")
    print(f"🌾 Kc: {kc:.2f}")
    print(f"💧 Smart Irrigation: {smart_irrigation:.2f} m³/day")
    print(f"💰 Savings: {savings}")
    return {
        "et0": et0,
        "ndvi": ndvi,
        "kc": kc,
        "smart_irrigation": smart_irrigation,
        "savings": savings
    }

# =====================================================
#  5️⃣ RUN TEST (Sousse Example)
# =====================================================
if __name__ == "__main__":
    run_irrigation_ai(lat=35.8, lon=10.6, traditional_amount=5.0, growth_stage='mid')
