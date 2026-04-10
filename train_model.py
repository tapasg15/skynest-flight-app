import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import pickle

print("🚀 Starting Machine Learning Training Process...")

# 1. Generate Realistic Synthetic Data (Historical Flights)
# In a real company, this comes from a database. Here we simulate 2000 flights.
np.random.seed(42)
n_samples = 2000

origins = np.random.choice(['Delhi', 'Mumbai', 'Bangalore', 'Goa', 'Chennai', 'Kolkata'], n_samples)
destinations = np.random.choice(['Delhi', 'Mumbai', 'Bangalore', 'Goa', 'Chennai', 'Kolkata'], n_samples)
hours = np.random.randint(0, 24, n_samples)

# Make realistic rules for delays (e.g., late night flights or specific routes delay more)
delays = []
for i in range(n_samples):
    delay_chance = 0.2  # Base 20% chance of delay
    
    if hours[i] >= 18 or hours[i] <= 3: # Evening/Night flights delay more
        delay_chance += 0.3
    if origins[i] == 'Mumbai' and destinations[i] == 'Delhi': # Busy route
        delay_chance += 0.2
        
    if np.random.rand() < delay_chance:
        delays.append('Delayed')
    else:
        delays.append('On Time')

# Create DataFrame
df = pd.DataFrame({'origin': origins, 'destination': destinations, 'hour': hours, 'status': delays})
# Remove rows where origin and destination are the same
df = df[df['origin'] != df['destination']]

# 2. Data Preprocessing (Encoding Text to Numbers)
print("⚙️ Preprocessing Data...")
le_origin = LabelEncoder()
le_dest = LabelEncoder()

df['origin_encoded'] = le_origin.fit_transform(df['origin'])
df['destination_encoded'] = le_dest.fit_transform(df['destination'])

X = df[['origin_encoded', 'destination_encoded', 'hour']]
y = df['status']

# 3. Train the Random Forest Model
print("🧠 Training Random Forest Classifier...")
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X, y)

accuracy = model.score(X, y)
print(f"✅ Model Trained Successfully! Accuracy: {accuracy*100:.2f}%")

# 4. Save the Model and Encoders (Pickling)
# We save these so Flask can use them later without retraining!
with open('delay_model.pkl', 'wb') as f:
    pickle.dump(model, f)

with open('encoders.pkl', 'wb') as f:
    pickle.dump({'origin': le_origin, 'destination': le_dest}, f)

print("💾 Model saved as 'delay_model.pkl' and 'encoders.pkl'")
print("🎉 You can now start your Flask app!")