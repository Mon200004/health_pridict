from flask import Flask, request, jsonify
import numpy as np
import pymysql
from firebase_admin import credentials, messaging, initialize_app
import os

app = Flask(__name__)

# Firebase Initialization
firebase_cred = credentials.Certificate("api/firebase-key.json")
initialize_app(firebase_cred)

# Database Configuration
DB_CONFIG = {
    "host": "db9801.public.databaseasp.net",
    "port": 3306,
    "user": "db9801",
    "password": "E%m7zD5!2s#F",
    "database": "db9801",
    "cursorclass": pymysql.cursors.DictCursor,
}

# Load pretrained model parameters
model_data = np.load(
    os.path.join(os.path.dirname(__file__), 'health_model.npy'), allow_pickle=True
).item()
weights = model_data['weights']
bias = model_data['bias']
mean = model_data['mean']
std = model_data['std']

# Helper function to predict health condition
def predict_health(sugar_percentage, avg_temperature, avg_blood_pressure):
    try:
        features = np.array([sugar_percentage, avg_temperature, avg_blood_pressure])
        normalized_features = (features - mean) / std
        health_prediction = np.dot(normalized_features, weights) + bias
        return float(health_prediction)
    except Exception as e:
        raise ValueError(f"Error during prediction: {str(e)}")

# Function to send notifications via Firebase
def send_notification_to_mobile(patient_id, health_condition):
    title = "Critical Health Alert"
    body = (
        f"Patient ID {patient_id} has a critical health condition of {health_condition}. Immediate attention required."
    )
    try:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            topic="hospital_alerts",
        )
        messaging.send(message)
    except Exception as e:
        raise RuntimeError(f"Error sending notification: {str(e)}")

# API route for health prediction and notification
@app.route('/api/predict', methods=['POST'])
def predict_and_notify():
    try:
        # Parse input data
        data = request.json
        patient_id = int(data['patient_id'])
        date = data['date']
        sugar_percentage = float(data['sugar_percentage'])
        avg_temperature = float(data['average_temperature'])
        avg_blood_pressure = float(data['average_blood_pressure'])
        hospital_id = int(data['hospital_id'])

        # Predict health condition
        health_condition = predict_health(sugar_percentage, avg_temperature, avg_blood_pressure)

        # Save data to the database
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()

        insert_query = """
            INSERT INTO biological_indicators (Patient_ID, Date, Sugar_Percentage, Average_Temperature, Blood_Pressure, health_condition, Hospital_ID)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (
            patient_id,
            date,
            sugar_percentage,
            avg_temperature,
            avg_blood_pressure,
            health_condition,
            hospital_id,
        ))
        connection.commit()

        # Check if health condition is critical and send notification
        if health_condition >= 60:
            send_notification_to_mobile(patient_id, health_condition)

        # Close the database connection
        cursor.close()
        connection.close()

        return jsonify({
            'status': 'success',
            'patient_id': patient_id,
            'date': date,
            'sugar_percentage': sugar_percentage,
            'average_temperature': avg_temperature,
            'average_blood_pressure': avg_blood_pressure,
            'predicted_health_condition': health_condition,
            'hospital_id': hospital_id,
            'message': 'Prediction made and data saved successfully.',
        }), 200

    except ValueError as ve:
        return jsonify({'status': 'error', 'message': str(ve)}), 400
    except RuntimeError as re:
        return jsonify({'status': 'error', 'message': str(re)}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Health check route
@app.route('/')
def health_check():
    return "API is running successfully!"

# Export WSGI app for deployment
wsgi_app = app.wsgi_app
