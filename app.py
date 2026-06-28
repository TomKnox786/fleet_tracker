import os
from flask import Flask, request, jsonify, render_template, Response
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, date
import math

app = Flask(__name__)
CORS(app)

database_url = os.environ.get("DATABASE_URL")

if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trucks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ✅ GEOFENCE SETTINGS
GEOFENCE_CENTER = (-15.3875, 28.3228)
GEOFENCE_RADIUS_METERS = 1000

class Truck(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    truck_id = db.Column(db.String(50), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

@app.route('/')
def dashboard():
    return render_template('index.html')

@app.route('/update_location', methods=['POST'])
def update_location():
    data = request.json

    new_location = Truck(
        truck_id=data['truck_id'],
        latitude=data['latitude'],
        longitude=data['longitude']
    )

    db.session.add(new_location)
    db.session.commit()

    return jsonify({"message": "Location updated successfully"})

# ✅ Distance calculator
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@app.route('/get_locations', methods=['GET'])
def get_locations():

    points = Truck.query.order_by(Truck.timestamp.desc()).limit(200).all()
    current_time = datetime.utcnow()

    result_raw = {}

    for p in points:

        # ✅ Online / Offline
        time_diff = (current_time - p.timestamp).total_seconds()
        status = "Online" if time_diff <= 15 else "Offline"

        # ✅ Geofence
        distance_km = haversine_km(
            p.latitude, p.longitude,
            GEOFENCE_CENTER[0], GEOFENCE_CENTER[1]
        )

        inside = (distance_km * 1000) <= GEOFENCE_RADIUS_METERS
        geofence_status = "Inside Depot" if inside else "Outside Depot"

        if p.truck_id not in result_raw:
            result_raw[p.truck_id] = []

        result_raw[p.truck_id].append({
            "latitude": p.latitude,
            "longitude": p.longitude,
            "timestamp_dt": p.timestamp,
            "status": status,
            "geofence": geofence_status
        })

    result = {}

    for truck_id, pos_list in result_raw.items():

        positions = []

        for item in pos_list:
            positions.append({
                "latitude": item["latitude"],
                "longitude": item["longitude"],
                "timestamp": item["timestamp_dt"].strftime("%Y-%m-%d %H:%M:%S"),
                "status": item["status"],
                "geofence": item["geofence"],
                "speed_kmh": None
            })

        # ✅ Speed from last two points
        if len(pos_list) >= 2:
            latest = pos_list[0]
            previous = pos_list[1]

            distance = haversine_km(
                latest["latitude"], latest["longitude"],
                previous["latitude"], previous["longitude"]
            )

            time_hours = (
                latest["timestamp_dt"] - previous["timestamp_dt"]
            ).total_seconds() / 3600.0

            if time_hours > 0:
                positions[0]["speed_kmh"] = round(distance / time_hours, 1)

        result[truck_id] = positions

    return jsonify(result)

@app.route('/daily_report', methods=['GET'])
def daily_report():

    today = date.today()
    start_of_day = datetime(today.year, today.month, today.day)

    records = Truck.query.filter(
        Truck.timestamp >= start_of_day
    ).order_by(Truck.truck_id, Truck.timestamp).all()

    report = {}

    for record in records:

        if record.truck_id not in report:
            report[record.truck_id] = {
                "total_distance_km": 0,
                "start_time": record.timestamp,
                "end_time": record.timestamp,
                "last_lat": record.latitude,
                "last_lon": record.longitude
            }
        else:
            prev_lat = report[record.truck_id]["last_lat"]
            prev_lon = report[record.truck_id]["last_lon"]

            distance = haversine_km(
                prev_lat, prev_lon,
                record.latitude, record.longitude
            )

            report[record.truck_id]["total_distance_km"] += distance
            report[record.truck_id]["end_time"] = record.timestamp
            report[record.truck_id]["last_lat"] = record.latitude
            report[record.truck_id]["last_lon"] = record.longitude

    final_report = {}

    for truck_id, data in report.items():

        active_hours = (
            data["end_time"] - data["start_time"]
        ).total_seconds() / 3600.0

        final_report[truck_id] = {
            "total_distance_km": round(data["total_distance_km"], 2),
            "start_time": data["start_time"].strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": data["end_time"].strftime("%Y-%m-%d %H:%M:%S"),
            "active_hours": round(active_hours, 2)
        }

    return jsonify(final_report)

@app.route('/export_daily_report', methods=['GET'])
def export_daily_report():

    today = date.today()
    start_of_day = datetime(today.year, today.month, today.day)

    records = Truck.query.filter(
        Truck.timestamp >= start_of_day
    ).order_by(Truck.truck_id, Truck.timestamp).all()

    report = {}

    for record in records:

        if record.truck_id not in report:
            report[record.truck_id] = {
                "total_distance_km": 0,
                "start_time": record.timestamp,
                "end_time": record.timestamp,
                "last_lat": record.latitude,
                "last_lon": record.longitude
            }
        else:
            prev_lat = report[record.truck_id]["last_lat"]
            prev_lon = report[record.truck_id]["last_lon"]

            distance = haversine_km(
                prev_lat, prev_lon,
                record.latitude, record.longitude
            )

            report[record.truck_id]["total_distance_km"] += distance
            report[record.truck_id]["end_time"] = record.timestamp
            report[record.truck_id]["last_lat"] = record.latitude
            report[record.truck_id]["last_lon"] = record.longitude

    def generate():
        yield "Truck ID,Total Distance (km),Start Time,End Time,Active Hours\n"

        for truck_id, data in report.items():

            active_hours = (
                data["end_time"] - data["start_time"]
            ).total_seconds() / 3600.0

            yield f"{truck_id},{round(data['total_distance_km'],2)},{data['start_time']},{data['end_time']},{round(active_hours,2)}\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=daily_report.csv"}
    )

if __name__ == '__main__':
   if __name__ == '__main__':
    app.run()