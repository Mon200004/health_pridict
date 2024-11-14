from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import numpy as np

app = Flask(__name__)
CORS(app)

# Load the pretrained model
model = joblib.load('health_model.pkl')

@app.route('/api/predict', methods=['POST'])
def predict():
    try:
        data = request.json
        sugar_percentage = data['sugar_percentage']
        average_temperature = data['average_temperature']
        systolic = data['systolic']
        diastolic = data['diastolic']

        # Prepare input data for prediction
        input_data = np.array([[sugar_percentage, average_temperature, systolic, diastolic]])
        prediction = model.predict(input_data)[0]

        # Return prediction result
        return jsonify({'predicted_health_state': int(prediction)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
