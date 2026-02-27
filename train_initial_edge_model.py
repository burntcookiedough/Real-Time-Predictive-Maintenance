import os
import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib
import config

def main():
    print("Training baseline Isolation Forest model...")
    
    # Load historical data
    try:
        df = pd.read_csv('ai4i2020.csv')
    except FileNotFoundError:
        print("Dataset ai4i2020.csv not found. Please ensure it is in the same directory.")
        return

    # For AI4I, we select continuous features for anomaly detection
    # Features: Air temperature, Process temperature, Rotational speed, Torque, Tool wear
    features = ['Air temperature [K]', 'Process temperature [K]', 'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]']
    
    X = df[features]
    
    # Initialize Isolation Forest
    # Contamination is the expected proportion of outliers (set to 5% as a baseline)
    model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    
    print("Fitting model...")
    model.fit(X)
    
    # Save the model
    joblib.dump(model, config.MODEL_PATH)
    print(f"Model saved to {config.MODEL_PATH}")

if __name__ == "__main__":
    main()
