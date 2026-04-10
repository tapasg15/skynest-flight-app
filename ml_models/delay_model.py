import pandas as pd
from sklearn.tree import DecisionTreeClassifier
import pickle

# 1. Provide dummy historical data for the AI to learn from.
data = {
    'route_code': [1, 2, 3, 1, 2, 3, 1, 2, 3, 1],
    'hour':       [8, 11, 9, 18, 22, 14, 9, 12, 21, 19],
    'delayed':    [0,  1, 0,  1,  1,  0, 0,  1,  0,  1] 
}

df = pd.DataFrame(data)

# 2. Split data into Features (X) and Target (y)
X = df[['route_code', 'hour']]
y = df['delayed']

# 3. Train the AI Model
print("Training the AI model...")
model = DecisionTreeClassifier()
model.fit(X, y)

# 4. Save the trained model's "brain" to a file
with open('delay_model.pkl', 'wb') as f:
    pickle.dump(model, f)

print("Success! AI Model trained and saved as 'delay_model.pkl'")