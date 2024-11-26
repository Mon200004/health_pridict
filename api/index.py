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
def predict_health(sugar_percentage, avg_temperature, avg_blood_pressure):
    try:
        features = np.array([sugar_percentage, avg_temperature, avg_blood_pressure])
        normalized_features = (features - mean) / std
        health_prediction = np.dot(normalized_features, weights) + bias
        return float(health_prediction)
    except Exception as e:
        return f"Error during prediction: {str(e)}"

# API route for prediction and database insertion
@app.route('/api/predict', methods=['POST'])
def predict():
    try:
        # Parse input data
        data = request.json
        patient_id = int(data['patient_id'])
        date = data['date']
        sugar_percentage = float(data['sugar_percentage'])
        avg_temperature = float(data['average_temperature'])
        avg_blood_pressure = float(data['average_blood_pressure'])
        hospital_id = int(data['hospital_id'])

        # Predict health state
        health_state = predict_health(sugar_percentage, avg_temperature, avg_blood_pressure)

        if isinstance(health_state, str):  # Handle prediction errors
            return jsonify({'error': health_state}), 400

        # Connect to the database and insert data
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()

        insert_query = """
        INSERT INTO biological_indicators (Patient_ID, Date, Sugar_Percentage, Average_Temperature, Blood_Pressure, health_condition, Hospital_ID)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (patient_id, date, sugar_percentage, avg_temperature, avg_blood_pressure, health_state, hospital_id))
        connection.commit()

        cursor.close()
        connection.close()

        # Return success response
        return jsonify({
            'patient_id': patient_id,
            'date': date,
            'sugar_percentage': sugar_percentage,
            'average_temperature': avg_temperature,
            'average_blood_pressure': avg_blood_pressure,
            'predicted_health_state': health_state,
            'hospital_id': hospital_id
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Explicit WSGI handler for Vercel
wsgi_app = app.wsgi_app
