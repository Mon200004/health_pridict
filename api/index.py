from flask import Flask, request, jsonify
import numpy as np
import pymysql
import os

# Load the pretrained model
model_weights = np.load(os.path.join(os.path.dirname(__file__), '../health_model.npy'))

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
    'db': 'db9801'
}

# Helper function to predict health condition
def predict_health(sugar_percentage, avg_temperature, blood_pressure):
    # Extract systolic and diastolic from the blood pressure string (e.g., "120/80")
    try:
        systolic, diastolic = map(int, blood_pressure.split('/'))
    except ValueError:
        return "Invalid blood pressure format. Use 'systolic/diastolic' format."

    features = np.array([sugar_percentage, avg_temperature, systolic, diastolic])
    features = (features - np.mean(features)) / np.std(features)
    features = np.insert(features, 0, 1)  # Add the bias term
    health_prediction = features @ model_weights
    return float(health_prediction)

# API route for prediction
@app.route('/api/predict', methods=['POST'])
def predict():
    try:
        data = request.json
        sugar_percentage = float(data['sugar_percentage'])
        avg_temperature = float(data['average_temperature'])
        blood_pressure = data['blood_pressure']  # Blood pressure as a single string (e.g., "120/80")

        # Predict the health state
        health_state = predict_health(sugar_percentage, avg_temperature, blood_pressure)

        # Check for prediction error
        if isinstance(health_state, str):  # If it's an error message
            return jsonify({'error': health_state}), 400

        # Connect to the database
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # Insert data into the database
        insert_query = """
        INSERT INTO biological_indicators (Sugar_Percentage, Average_Temperature, Blood_Pressure, health_condition)
        VALUES (%s, %s, %s, %s)
        """
        cursor.execute(insert_query, (sugar_percentage, avg_temperature, blood_pressure, health_state))
        connection.commit()

        cursor.close()
        connection.close()

        # Return the prediction response
        return jsonify({
            'sugar_percentage': sugar_percentage,
            'average_temperature': avg_temperature,
            'blood_pressure': blood_pressure,
            'predicted_health_state': health_state
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Explicit WSGI handler for Vercel
wsgi_app = app.wsgi_app
