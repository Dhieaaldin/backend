from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/savings", methods=["POST"])
def calculate_savings():
    data = request.get_json()
    traditional = data["traditional"]
    smart = data["smart"]

    water_saved_liters = (traditional - smart) * 1000
    percentage_saved = ((traditional - smart) / traditional) * 100
    cost_saved_tnd = water_saved_liters * 0.0005

    return jsonify({
        "water_saved_liters": round(water_saved_liters, 2),
        "water_saved_m3": round(traditional - smart, 2),
        "percentage_saved": round(percentage_saved, 2),
        "cost_saved_tnd": round(cost_saved_tnd, 2),
        "cost_saved_usd": round(cost_saved_tnd * 0.32, 2)
    })

if __name__ == "__main__":
    app.run(port=5005, debug=True)
