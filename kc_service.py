from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/kc", methods=["GET"])
def calculate_kc():
    ndvi = float(request.args.get("ndvi"))
    stage = request.args.get("stage", "mid")
    base_kc = {'initial': 0.50, 'mid': 0.65, 'late': 0.60}

    if ndvi < 0.3:
        adj = 0.15
    elif ndvi < 0.5:
        adj = 0.10
    elif ndvi < 0.7:
        adj = 0.05
    else:
        adj = 0.0

    kc = base_kc.get(stage, 0.65) + adj
    return jsonify({"kc": round(kc, 2)})

if __name__ == "__main__":
    app.run(port=5004, debug=True)
