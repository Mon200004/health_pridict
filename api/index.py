from flask import Flask, request, jsonify
import numpy as np
import pymysql
import os
from werkzeug.middleware.proxy_fix import ProxyFix

# Load the pretrained model
model_weights = np.load(os.path.join(os.path.dirname(__file__), 'health_condition_model.npy'))

# Initialize the Flask app
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)

# Database connection details
DB_CONFIG = {
    'host': 'db9801.public.databaseasp.net',
    'port': 3306,
    'user': 'db9801',
    'password': 'E%m7zD5!2s#F',
    'db': 'db9801'
}

# Helper function to predict health condition
def predict_health(sugar_percentage, avg_temperature, systolic, diastolic):
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
        systolic = float(data['systolic'])
        diastolic = float(data['diastolic'])

        health_state = predict_health(sugar_percentage, avg_temperature, systolic, diastolic)

        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()

        insert_query = """
        INSERT INTO biological_indicators (Sugar_Percentage, Average_Temperature, Systolic, Diastolic, health_condition)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (sugar_percentage, avg_temperature, systolic, diastolic, health_state))
        connection.commit()

        cursor.close()
        connection.close()

        return jsonify({
            'sugar_percentage': sugar_percentage,
            'average_temperature': avg_temperature,
            'systolic': systolic,
            'diastolic': diastolic,
            'predicted_health_state': health_state
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Explicit handler for Vercel
from flask import Request as VercelRequest
from werkzeug.wrappers import Response

def handler(vercel_request: VercelRequest) -> Response:
    return app(vercel_request.environ, start_response=lambda x, y: None)
