from flask import Flask, request, jsonify
import numpy as np
import json
import os
from datetime import datetime
import pymysql
import requests

app = Flask(__name__)

# Load Firebase server key from JSON file
FIREBASE_KEY_PATH = os.path.join(os.path.dirname(__file__), 'firebase-key.json')

try:
    with open(FIREBASE_KEY_PATH, 'r') as f:
        firebase_config = json.load(f)
    FIREBASE_SERVER_KEY = firebase_config.get('server_key')
except Exception as e:
    raise RuntimeError(f"Failed to load Firebase server key: {e}")

FIREBASE_URL = "https://fcm.googleapis.com/fcm/send"

# Pretrained model parameters
model_data = np.load('api/health_model.npy', allow_pickle=True).item()
weights = model_data['weights']
bias = model_data['bias']
mean = model_data['mean']
std = model_data['std']

# Database configuration
DB_CONFIG = {
    'host': 'db9801.public.databaseasp.net',
    'port': 3306,
    'user': 'db9801',
    'password': 'E%m7zD5!2s#F',
    'database': 'db9801'
}

# Predict health condition
def predict_health(sugar_percentage, avg_temperature, avg_blood_pressure):
    try:
        features = np.array([sugar_percentage, avg_temperature, avg_blood_pressure])
        normalized_features = (features - mean) / std
        health_prediction = np.dot(normalized_features, weights) + bias
        return round(float(health_prediction), 2)
    except Exception as e:
        raise ValueError(f"Prediction error: {e}")

# Send notification to Firebase
def send_notification_to_topic(title, body, topic="hospital_alerts"):
    headers = {
        "Authorization": f"key={FIREBASE_SERVER_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "to": f"/topics/{topic}",
        "notification": {
            "title": title,
            "body": body
        }
    }
    try:
        response = requests.post(FIREBASE_URL, headers=headers, data=json.dumps(payload))
        return response.status_code, response.json()
    except Exception as e:
        return None, {"error": str(e)}

# API health check
@app.route('/')
def home():
    return "API is running successfully!"

# Endpoint for prediction and data insertion
@app.route('/api/predict', methods=['POST'])
def predict_and_store():
    try:
        # Parse request data
        data = request.get_json()
        patient_id = data.get('patient_id')
        date = data.get('date')
        sugar_percentage = float(data.get('sugar_percentage'))
        avg_temperature = float(data.get('average_temperature'))
        avg_blood_pressure = float(data.get('average_blood_pressure'))
        hospital_id = data.get('hospital_id')

        # Predict health condition
        health_condition = predict_health(sugar_percentage, avg_temperature, avg_blood_pressure)

        # Insert data into the database
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()
        insert_query = """
            INSERT INTO biological_indicators (Patient_ID, Date, Sugar_Percentage, Average_Temperature, Blood_Pressure, health_condition, Hospital_ID)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (patient_id, date, sugar_percentage, avg_temperature, avg_blood_pressure, health_condition, hospital_id))
        connection.commit()

        # Check for critical health condition and send notification
        if health_condition >= 60:
            title = "Critical Health Alert"
            body = f"Patient ID {patient_id} has a critical health condition of {health_condition}."
            send_notification_to_topic(title, body)

        cursor.close()
        connection.close()

        # Return response
        return jsonify({
            'status': 'success',
            'patient_id': patient_id,
            'date': date,
            'sugar_percentage': sugar_percentage,
            'average_temperature': avg_temperature,
            'average_blood_pressure': avg_blood_pressure,
            'predicted_health_state': health_condition,
            'hospital_id': hospital_id
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Endpoint to manually trigger notifications
@app.route('/api/notify-critical-patients', methods=['POST'])
def notify_critical_patients():
    try:
        # Connect to the database
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor(pymysql.cursors.DictCursor)

        # Fetch critical patients
        query = """
            SELECT b.Patient_ID, b.health_condition, b.Date, p.Mobile_Number, p.Age
            FROM biological_indicators b
            JOIN patients p ON b.Patient_ID = p.ID
            WHERE b.health_condition >= 60
            AND b.Date = CURDATE()
        """
        cursor.execute(query)
        critical_patients = cursor.fetchall()

        # Send notifications for each critical patient
        for patient in critical_patients:
            title = "Critical Patient Alert"
            body = f"Patient ID {patient['Patient_ID']} (Age: {patient['Age']}) has a critical health condition of {patient['health_condition']}."
            send_notification_to_topic(title, body)

        cursor.close()
        connection.close()

        return jsonify({"status": "success", "message": "Notifications sent"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Vercel-specific handler
wsgi_app = app.wsgi_app

if __name__ == "__main__":
    app.run(debug=True)
