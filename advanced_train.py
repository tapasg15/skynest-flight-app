import pandas as pd
import numpy as np
import pickle
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import LabelEncoder

print("🚀 Starting Advanced AI Training Pipeline...")

# ==========================================
# STEP 1: BIG DATA GENERATION (Simulating 5000 Flights)
# ==========================================
print("📊 Generating 5000 rows of realistic flight data...")
np.random.seed(42)

origins = ['Delhi', 'Mumbai', 'Bangalore', 'Kolkata', 'Goa', 'Pune', 'Ranchi', 'Indore']
destinations = ['Mumbai', 'Delhi', 'Bangalore', 'Goa', 'Kolkata', 'Pune', 'Ranchi', 'Indore']

data = []
for _ in range(5000):
    o = np.random.choice(origins)
    d = np.random.choice(destinations)
    while o == d: # Flight same city me nahi ja sakti
        d = np.random.choice(destinations) 
        
    hour = np.random.randint(0, 24)
    
    # --- REALISTIC DELAY LOGIC (The Secret Sauce) ---
    delay_probability = 0.15 # Base chance of delay is 15%
    
    # 1. Raat ki flights zyada late hoti hain
    if hour >= 18 or hour <= 3: 
        delay_probability += 0.25 
        
    # 2. Busy airports (Delhi/Mumbai) par traffic ki wajah se delay
    if o in ['Delhi', 'Mumbai'] and d in ['Delhi', 'Mumbai']: 
        delay_probability += 0.20
        
    # Status assign karna probabilities ke basis par (0 = On Time, 1 = Delayed)
    status = 1 if np.random.rand() < delay_probability else 0
    data.append([o, d, hour, status])

# Data ko CSV mein save karna (Aapki file ban jayegi!)
df = pd.DataFrame(data, columns=['origin', 'destination', 'hour_of_day', 'status'])
df.to_csv('large_flight_data.csv', index=False)
print("✅ 'large_flight_data.csv' created successfully!")

# ==========================================
# STEP 2: DATA ENCODING & PREPARATION
# ==========================================
encoders = {}
for col in ['origin', 'destination']:
    le = LabelEncoder()
    df[col] = le.fit_transform(df[col])
    encoders[col] = le

X = df[['origin', 'destination', 'hour_of_day']]
y = df['status']

# Data ko Train (80%) aur Test (20%) mein todna
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ==========================================
# STEP 3: HYPERPARAMETER TUNING (The Boost!)
# ==========================================
print("🧠 Training Tuned Random Forest Model...")
# Humne trees (n_estimators) badha diye aur max_depth set kar di taaki model overthink na kare
model = RandomForestClassifier(
    n_estimators=250,      # 250 Decision trees milkar vote karenge
    max_depth=10,          # Depth control for better accuracy
    random_state=42, 
    class_weight='balanced' # Delay aur On-Time data ko balance karna
)
model.fit(X_train, y_train)

# ==========================================
# STEP 4: TEST THE ACCURACY
# ==========================================
predictions = model.predict(X_test)
accuracy = accuracy_score(y_test, predictions)
print(f"🎯 Model Accuracy on unseen test data: {accuracy * 100:.2f}%")

# ==========================================
# STEP 5: SAVE THE SUPERCHARGED MODEL
# ==========================================
with open('delay_model.pkl', 'wb') as f:
    pickle.dump(model, f)
with open('encoders.pkl', 'wb') as f:
    pickle.dump(encoders, f)

print("✅ Supercharged Models saved! Restart your Flask server to use them.")