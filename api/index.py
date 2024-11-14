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
    # Extract systolic and diastolic from the blood pressure string (e.g., "120/80")
    try:
        systolic, diastolic = map(int, blood_pressure.split('/'))
    except ValueError:
        return "Invalid blood pressure format. Use 'systolic/diastolic' format."

    # Create the feature array and normalize using the stored mean and std from training
    features = np.array([sugar_percentage, avg_temperature, systolic, diastolic])
    normalized_features = (features - mean) / std

    # Calculate the health state as a linear combination of the normalized features, weights, and bias
    health_prediction = np.dot(normalized_features, weights) + bias
    return float(health_prediction)

# API route for prediction
@app.route('/api/predict', methods=['POST'])
def predict():
    try:
        data = request.json
        
        # Validate that all required fields are present
        required_fields = ['patient_id', 'date', 'sugar_percentage', 'average_temperature', 'blood_pressure']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f"Missing required field: {field}"}), 400
        
        # Parse and validate the input data
        patient_id = data['patient_id']
        date = data['date']
        sugar_percentage = float(data['sugar_percentage'])
        avg_temperature = float(data['average_temperature'])
        blood_pressure = data['blood_pressure']
        
        # Predict the health state
        health_state = predict_health(sugar_percentage, avg_temperature, blood_pressure)
        
        if isinstance(health_state, str):  # Check for prediction error message
            return jsonify({'error': health_state}), 400
        
        # Connect to the database
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        # Insert data into the database
        insert_query = """
        INSERT INTO biological_indicators (Patient_ID, Date, Sugar_Percentage, Average_Temperature, Blood_Pressure, health_condition)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (patient_id, date, sugar_percentage, avg_temperature, blood_pressure, health_state))
        connection.commit()
        
        # Close the database connection
        cursor.close()
        connection.close()
        
        # Return the prediction response
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

if __name__ == '__main__':
    app.run(debug=True)
