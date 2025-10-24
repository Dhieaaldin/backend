from flask import Flask, request, jsonify
import math

app = Flask(__name__)

@app.route("/et0", methods=["POST"])
def calculate_et0():
    data = request.get_json()
    temp_max = data["temp_max"]
    temp_min = data["temp_min"]
    humidity = data["humidity"]
    wind_speed = data["wind_speed"]
    latitude = data["latitude"]
    day_of_year = data["day_of_year"]

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

    return jsonify({"et0": round(max(0, et0), 2)})

if __name__ == "__main__":
    app.run(port=5003, debug=True)
