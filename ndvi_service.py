from flask import Flask, request, jsonify
import datetime
import ee

app = Flask(__name__)

try:
    ee.Initialize()
    GEE_AVAILABLE = True
except Exception:
    GEE_AVAILABLE = False
    print("⚠️ GEE not initialized, NDVI will use fallback.")

def get_ndvi_from_gee(lat, lon, start_date, end_date):
    point = ee.Geometry.Point([lon, lat])
    collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                  .filterBounds(point)
                  .filterDate(start_date, end_date)
                  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)))
    ndvi_collection = collection.map(lambda img:
        img.addBands(img.normalizedDifference(['B8', 'B4']).rename('NDVI')))
    ndvi_image = ndvi_collection.mean().select('NDVI')
    ndvi_value = ndvi_image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=point,
        scale=10
    ).get('NDVI').getInfo()
    if ndvi_value is None:
        ndvi_value = 0.6
    return round(ndvi_value, 2)

@app.route("/ndvi", methods=["GET"])
def get_ndvi():
    lat = float(request.args.get("lat"))
    lon = float(request.args.get("lon"))
    today = datetime.date.today()
    start = today - datetime.timedelta(days=10)
    end = today
    if GEE_AVAILABLE:
        try:
            ndvi = get_ndvi_from_gee(lat, lon, str(start), str(end))
        except Exception as e:
            print("⚠️ NDVI error:", e)
            ndvi = 0.6
    else:
        ndvi = 0.6
    return jsonify({"ndvi": ndvi})

if __name__ == "__main__":
    app.run(port=5002, debug=True)
