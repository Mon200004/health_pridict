from flask import Flask, request, jsonify
import numpy as np
import pymysql
import os

# Load the pretrained model parameters from .npy file
model_data = np.load(os.path.join(os.path.dirname(__file__), 'health_model.npy'), allow_pickle=True).item()
weights = model_data['weights']
bias = model_data['bias']
mean = model_data['mean']
std = model_data['std']

# Initialize the Flask app
app = Flask(__name__)

# Health check route
@app.route('/')
def home():
    return "API is running successfully!"

# Database connection details
DB_CONFIG = {
    'host': 'db9801.public.databaseasp.net',
    'port': 3306,
    'user': 'db9801',
    'password': 'E%m7zD5!2s#F',
    'db': 'db9801',
    'cursorclass': pymysql.cursors.DictCursor
}

# Helper function to predict health condition
def predict_health(sugar_percentage, avg_temperature, blood_pressure):
    try:
        systolic, diastolic = map(int, blood_pressure.split('/'))
    except ValueError:
        return "Invalid blood pressure format. Use 'systolic/diastolic' format."

    features = np.array([sugar_percentage, avg_temperature, systolic, diastolic])
    normalized_features = (features - mean) / std
    health_prediction = np.dot(normalized_features, weights) + bias
    return float(health_prediction)

# API route for prediction and database insertion
@app.route('/api/predict', methods=['POST'])
def predict():
    try:
        data = request.json
        patient_id = int(data['patient_id'])
        date = data['date']
        sugar_percentage = float(data['sugar_percentage'])
        avg_temperature = float(data['average_temperature'])
        blood_pressure = data['blood_pressure']

        health_state = predict_health(sugar_percentage, avg_temperature, blood_pressure)

        if isinstance(health_state, str):
            return jsonify({'error': health_state}), 400

        # Connect to the database and insert all data in one operation
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()

        insert_query = """
        INSERT INTO biological_indicators (Patient_ID, Date, Sugar_Percentage, Average_Temperature, Blood_Pressure, health_condition)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (patient_id, date, sugar_percentage, avg_temperature, blood_pressure, health_state))
        connection.commit()

        cursor.close()
        connection.close()

        return jsonify({
            'patient_id': patient_id,
            'date': date,
            'sugar_percentage': sugar_percentage,
            'average_temperature': avg_temperature,
            'blood_pressure': blood_pressure,
            'predicted_health_state': health_state
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Explicit WSGI handler for Vercel
wsgi_app = app.wsgi_app
