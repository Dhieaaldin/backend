from flask import Flask, request, jsonify
import datetime
import requests

app = Flask(__name__)
OPENWEATHER_API_KEY = "aef834001409e4023841f3aaddf0ab1d"

@app.route("/weather", methods=["GET"])
def get_weather():
    lat = float(request.args.get("lat"))
    lon = float(request.args.get("lon"))

    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
    r = requests.get(url)
    data = r.json()

    temp_max = data["main"]["temp_max"]
    temp_min = data["main"]["temp_min"]
    humidity = data["main"]["humidity"]
    wind_speed = data["wind"]["speed"]

    return jsonify({
        "temp_max": temp_max,
        "temp_min": temp_min,
        "humidity": humidity,
        "wind_speed": wind_speed,
        "latitude": lat,
        "day_of_year": datetime.date.today().timetuple().tm_yday
    })

if __name__ == "__main__":
    app.run(port=5001, debug=True)
