import json
import os
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from kafka import KafkaConsumer
import config

TRAIN_THRESHOLD = 500  # Number of new rows before triggering retraining

def json_deserializer(data):
    return json.loads(data.decode('utf-8'))

class SimpleAutoencoder(nn.Module):
    def __init__(self, input_dim):
        super(SimpleAutoencoder, self).__init__()
        # Encoder
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 8),
            nn.ReLU(),
            nn.Linear(8, 4) # Latent space
        )
        # Decoder
        self.decoder = nn.Sequential(
            nn.Linear(4, 8),
            nn.ReLU(),
            nn.Linear(8, 16),
            nn.ReLU(),
            nn.Linear(16, input_dim)
        )

    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded

def train_model(data_path, model_path):
    print("\n--- Waking up for Cloud Retraining ---")
    
    # Load historical data
    try:
        df = pd.read_csv(data_path)
    except Exception as e:
        print(f"Error loading data for training: {e}")
        return

    # Basic preprocessing
    features = ['Air temperature [K]', 'Process temperature [K]', 'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]']
    
    # Drop rows with missing features
    df = df.dropna(subset=features)
    if len(df) < 50:
         print("Not enough valid data to train.")
         return

    X = df[features].values
    
    # Normalize data (simple min-max for demo purposes)
    X_min = X.min(axis=0)
    X_max = X.max(axis=0)
    # Avoid division by zero
    X_range = X_max - X_min
    X_range[X_range == 0] = 1
    X_norm = (X - X_min) / X_range

    # Convert to PyTorch tensors
    tensor_x = torch.Tensor(X_norm)
    dataset = TensorDataset(tensor_x, tensor_x) # Autoencoder tries to predict its input
    dataloader = DataLoader(dataset, batch_size=32, shuffle=True)
    
    # Initialize model, loss, optimizer
    model = SimpleAutoencoder(input_dim=len(features))
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.01)

    # Training loop
    epochs = 10
    print(f"Training on {len(df)} historical records for {epochs} epochs...")
    model.train()
    for epoch in range(epochs):
        total_loss = 0
        for batch_features, _ in dataloader:
            optimizer.zero_grad()
            outputs = model(batch_features)
            loss = criterion(outputs, batch_features)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        
        if (epoch + 1) % 5 == 0:
            print(f"Epoch [{epoch+1}/{epochs}], Loss: {total_loss/len(dataloader):.4f}")
            
    # Save the new model weights
    torch.save(model.state_dict(), model_path + ".pt")
    print(f"New global model trained and saved to {model_path}.pt")
    print("--- Retraining Complete ---")


def main():
    print("Starting Cloud Node Simulator...")
    
    # Ensure the historical data file has headers if it doesn't exist
    if not os.path.exists(config.CLOUD_DATA_PATH):
        # We'll just define basic headers for the CSV
        pd.DataFrame(columns=['timestamp', 'Air temperature [K]', 'Process temperature [K]', 'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]', 'routing', 'latency_ms']).to_csv(config.CLOUD_DATA_PATH, index=False)

    consumer = KafkaConsumer(
        bootstrap_servers=[config.KAFKA_BROKER],
        auto_offset_reset='latest',
        group_id='cloud_processing_group',
        value_deserializer=json_deserializer
    )

    # Listen to both topics
    consumer.subscribe([config.TOPIC_ALERTS, config.TOPIC_CLOUD])
    print(f"Listening on topics: {config.TOPIC_ALERTS}, {config.TOPIC_CLOUD}")

    records_since_last_train = 0
    total_alerts = 0
    
    try:
        with open(config.CLOUD_DATA_PATH, 'a') as f:
            for message in consumer:
                topic = message.topic
                data = message.value
                
                if topic == config.TOPIC_ALERTS:
                    total_alerts += 1
                    print(f"[EDGE ALERT RUNTIME] Received anomaly alert. Total alerts: {total_alerts}")
                    # Could store alert metadata here
                    
                elif topic == config.TOPIC_CLOUD:
                    # Save filtered/raw data to historical DB/CSV
                    
                    row_data = [
                        data.get('timestamp', ''),
                        data.get('Air temperature [K]', ''),
                        data.get('Process temperature [K]', ''),
                        data.get('Rotational speed [rpm]', ''),
                        data.get('Torque [Nm]', ''),
                        data.get('Tool wear [min]', ''),
                        data.get('routing', ''),
                        data.get('latency_ms', '')
                    ]
                    
                    csv_line = ",".join(map(str, row_data)) + "\n"
                    f.write(csv_line)
                    f.flush() # Ensure it's written immediately
                    
                    records_since_last_train += 1
                    
                    # Periodic Retraining Check
                    if records_since_last_train >= TRAIN_THRESHOLD:
                        print(f"Threshold reached ({TRAIN_THRESHOLD} new records). Triggering retraining...")
                        train_model(config.CLOUD_DATA_PATH, config.MODEL_PATH)
                        records_since_last_train = 0

    except KeyboardInterrupt:
        print("\nCloud Node stopped by user.")
    finally:
        consumer.close()
        print("Kafka consumer closed.")

if __name__ == "__main__":
    main()
