from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)  # ✅ Allow all origins by default

SERVICES = {
    "weather": "http://localhost:5001/weather",
    "ndvi": "http://localhost:5002/ndvi",
    "et0": "http://localhost:5003/et0",
    "kc": "http://localhost:5004/kc",
    "savings": "http://localhost:5005/savings"
}

@app.route("/run_irrigation", methods=["GET"])
def run_irrigation():
    lat = float(request.args.get("lat"))
    lon = float(request.args.get("lon"))
    traditional_amount = float(request.args.get("traditional", 5.0))
    stage = request.args.get("stage", "mid")

    # 1️⃣ Get weather
    weather = requests.get(SERVICES["weather"], params={"lat": lat, "lon": lon}).json()

    # 2️⃣ Get NDVI
    ndvi = requests.get(SERVICES["ndvi"], params={"lat": lat, "lon": lon}).json()["ndvi"]

    # 3️⃣ Get ET0
    et0 = requests.post(SERVICES["et0"], json=weather).json()["et0"]

    # 4️⃣ Get Kc
    kc = requests.get(SERVICES["kc"], params={"ndvi": ndvi, "stage": stage}).json()["kc"]

    # 5️⃣ Smart irrigation and savings
    smart_irrigation = et0 * kc * 0.1
    savings = requests.post(SERVICES["savings"], json={
        "traditional": traditional_amount,
        "smart": smart_irrigation
    }).json()

    return jsonify({
        "ndvi": ndvi,
        "et0": et0,
        "kc": kc,
        "smart_irrigation": round(smart_irrigation, 2),
        "savings": savings
    })

if __name__ == "__main__":
    app.run(port=5000, debug=True)
