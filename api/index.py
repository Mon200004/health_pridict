from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import pymysql
import os

# Load the pretrained model
model_weights = np.load(os.path.join(os.path.dirname(__file__), 'health_condition_model.npy'))

# Initialize the Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

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
    'cursorclass': pymysql.cursors.DictCursor  # To return results as dictionaries
}

# Helper function to predict health condition
def predict_health(sugar_percentage, avg_temperature, systolic, diastolic):
    try:
        # Normalize the features
        features = np.array([sugar_percentage, avg_temperature, systolic, diastolic])
        features = (features - np.mean(features)) / np.std(features)
        features = np.insert(features, 0, 1)  # Add the bias term for prediction
        health_prediction = features @ model_weights
        return float(health_prediction)
    except Exception as e:
        print(f"Prediction Error: {e}")
        return None

# API route for prediction
@app.route('/api/predict', methods=['POST'])
def predict():
    try:
        data = request.json
        sugar_percentage = float(data.get('sugar_percentage', 0))
        avg_temperature = float(data.get('average_temperature', 0))
        systolic = float(data.get('systolic', 0))
        diastolic = float(data.get('diastolic', 0))

        # Perform the health prediction
        health_state = predict_health(sugar_percentage, avg_temperature, systolic, diastolic)

        if health_state is None:
            return jsonify({'error': 'Prediction failed.'}), 500

        # Connect to the database
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # Insert the data into the database
            insert_query = """
            INSERT INTO biological_indicators (Sugar_Percentage, Average_Temperature, Systolic, Diastolic, health_condition)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (sugar_percentage, avg_temperature, systolic, diastolic, health_state))
            connection.commit()

        return jsonify({
            'sugar_percentage': sugar_percentage,
            'average_temperature': avg_temperature,
            'systolic': systolic,
            'diastolic': diastolic,
            'predicted_health_state': health_state
        })

    except Exception as e:
        print(f"API Error: {e}")
        return jsonify({'error': str(e)}), 500

# Explicit WSGI handler for Vercel
wsgi_app = app.wsgi_app
