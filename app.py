from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import pickle
import pandas as pd
from datetime import datetime
import random
from google import genai
from google.genai import types
import time
import string
import numpy as np
import os


try:
    # Kyunki aapki dono .pkl files seedha main folder mein hain (app.py ke sath)
    model_path = os.path.join(os.path.dirname(__file__), 'delay_model.pkl')
    encoders_path = os.path.join(os.path.dirname(__file__), 'encoders.pkl')
    
    with open(model_path, 'rb') as f:
        ai_model = pickle.load(f)
        
    with open(encoders_path, 'rb') as f:
        encoders = pickle.load(f)
        
    print("✅ Machine Learning Models Loaded Successfully!")
except Exception as e:
    print(f"⚠️ Warning: Could not load ML models. Error: {e}")
    ai_model = None
    encoders = None

app = Flask(__name__)
# SECURITY KEY: This encrypts the user's session cookies so they stay logged in securely.
app.secret_key = 'super_secret_mca_project_key' 

CURRENT_ENV = 'local' #agar cloud se chalana hai to 'cloud' likh do or db se to 'local'

def get_db_connection():
    if CURRENT_ENV == 'cloud':
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='12Iphone@', #  MySQL password
            database='flight_db'
        )
    else:
        #  cloud setup
        conn = mysql.connector.connect(
            host='bpgjzfss3vtyb64bbs9g-mysql.services.clever-cloud.com',
            user='umw2xsat9vwhcbtu',
            password='1YJvDtdZSmeGEd2toh7y',
            database='bpgjzfss3vtyb64bbs9g'
        )
    return conn

# --- THE HOMEPAGE ROUTE (This went missing!) ---
@app.route('/')
def home():
    return render_template('index.html')

# --- THE ADMIN ROUTE ---
@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/api/flights', methods=['GET'])
def get_flights():
    # URL se 'origin' aur 'destination' nikalna (e.g., /api/flights?origin=Delhi)
    origin = request.args.get('origin', '').strip()
    destination = request.args.get('destination', '').strip()
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Base Query: Sab flights select karo
    query = "SELECT * FROM flights WHERE 1=1"
    params = []
    
    # Agar user ne 'From' city bhari hai
    if origin:
        query += " AND origin LIKE %s"
        params.append(f"%{origin}%")
        
    # Agar user ne 'To' city bhari hai
    if destination:
        query += " AND destination LIKE %s"
        params.append(f"%{destination}%")
        
    cursor.execute(query, tuple(params))
    flights = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return jsonify(flights)

# --- API: DELETE FLIGHT (UPGRADED) ---
@app.route('/api/delete_flight/<int:flight_id>', methods=['DELETE'])
def delete_flight(flight_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Flight ko udane ki koshish
        cursor.execute("DELETE FROM flights WHERE id = %s", (flight_id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({"success": True, "message": "Flight deleted successfully!"})
        
    except Exception as e:
        # Pata lagate hain exact error kya hai
        error_msg = str(e)
        print(f"🔥 EXACT BACKEND ERROR: {error_msg}")
        
        if "foreign key constraint" in error_msg.lower():
            return jsonify({"success": False, "message": "Cannot delete: Users have already booked tickets for this flight!"})
            
        return jsonify({"success": False, "message": f"Database Error: {error_msg}"})


# --- API: BUDGET FLIGHT OPTIMIZER ---
@app.route('/api/budget_deals', methods=['GET'])
def get_budget_deals():
    # User ka budget nikalna (Default ₹5000 agar kuch na bheje)
    max_budget = request.args.get('max_price', 5000, type=float)
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # SQL Query: Sirf budget ke andar wali flights lao aur sasti wali pehle dikhao
    query = "SELECT * FROM flights WHERE price <= %s ORDER BY price ASC LIMIT 4"
    cursor.execute(query, (max_budget,))
    deals = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return jsonify(deals)


# --- API: ADD A NEW FLIGHT ---
@app.route('/api/add_flight', methods=['POST'])
def add_flight():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        INSERT INTO flights (flight_number, origin, destination, departure_time, price, status) 
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    values = (
        data['flight_number'], 
        data['origin'], 
        data['destination'], 
        data['departure_time'], 
        data['price'], 
        data['status']
    )
    
    cursor.execute(query, values)
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Flight added successfully!"})

# --- REAL MACHINE LEARNING INFERENCE ---
@app.route('/api/predict', methods=['POST'])
def predict_delay():
    try:
        # Check if models loaded properly
        if 'ai_model' not in globals() or ai_model is None:
            return jsonify({"prediction": "Model Offline"})

        data = request.json
        
        # .strip() removes any hidden spaces from the database text
        origin = data.get('origin', '').strip()
        destination = data.get('destination', '').strip()
        hour = int(data.get('hour', 0))
        
        # Safety Check: Did the model see this city during training?
        if origin not in encoders['origin'].classes_ or destination not in encoders['destination'].classes_:
            return jsonify({"prediction": "New Route (No Data)"})

        # Encode text to numbers
        orig_encoded = encoders['origin'].transform([origin])[0]
        dest_encoded = encoders['destination'].transform([destination])[0]
        
        # Prepare data for prediction
        input_data = pd.DataFrame([[orig_encoded, dest_encoded, hour]],
                                  columns=['origin', 'destination', 'hour_of_day'])
                # Get prediction
        raw_prediction = ai_model.predict(input_data)[0]
        
            # Numpy int64 ko normal Python number me badal kar Text banayein
        final_result = "Delayed" if int(raw_prediction) == 1 else "On Time"
        return jsonify({"prediction": final_result})
        
    except Exception as e:
        # THIS IS THE MAGIC LINE: It prints the EXACT error in your VS Code terminal!
        print(f"🔥 AI PREDICTION CRASHED: {str(e)}") 
        return jsonify({"prediction": "Backend Error"})


# --- AUTHENTICATION ROUTES ---

# 1. Show the Login/Register Page
@app.route('/auth')
def auth_page():
    return render_template('auth.html')

# 2. Handle User Registration (UPDATED WITH PHONE)
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    raw_email = data['email'].strip()
    phone = data['phone'].strip()
    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (full_name, email, phone, password_hash) VALUES (%s, %s, %s, %s)",
            (data['name'], raw_email, phone, hashed_password)
        )
        conn.commit()
        return jsonify({"success": True, "message": "Registration successful! Please log in."})
    except mysql.connector.IntegrityError:
        return jsonify({"success": False, "message": "Email or Phone already registered."}), 400
    finally:
        cursor.close()
        conn.close()

# 3. Handle User Login (STRICT)
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    raw_email = data['email'].strip()
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # MySQL fetches the user (case-insensitive)
    cursor.execute("SELECT * FROM users WHERE email = %s", (raw_email,))
    user = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if user:
        # ENHANCED SECURITY: Python forces a strict case-sensitive check!
        if user['email'] != raw_email:
            return jsonify({
                "success": False, 
                "message": "Security Alert: Email casing does not match our records exactly."
            }), 401

        # Check the password
        if check_password_hash(user['password_hash'], data['password']):
            session['user_id'] = user['id']
            session['user_name'] = user['full_name']
            session['user_role'] = user['role']
            return jsonify({"success": True, "message": "Login successful!", "redirect": "/"})
            
    # If the user doesn't exist or the password fails
    return jsonify({"success": False, "message": "Invalid email or password."}), 401

# 4. Handle Logout
@app.route('/logout')
def logout():
    session.clear() # Destroys the secure session
    return redirect(url_for('home'))

# --- PROFILE & BOOKINGS DASHBOARD ---

# 1. Show the Profile Page
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('auth_page'))
    return render_template('profile.html')
# Bookings
@app.route('/api/my_bookings')
def my_bookings():
    if 'user_id' not in session:
        return jsonify([])
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # FIX 1: Added f.price and b.booking_date in SELECT query
        query = """
            SELECT b.id as booking_id, b.pnr, b.seat_number as seat, b.gate, b.booking_date,
                   f.flight_number, f.origin, f.destination, f.departure_time, f.status, f.price 
            FROM bookings b 
            JOIN flights f ON b.flight_id = f.id 
            WHERE b.user_id = %s
            ORDER BY b.booking_date DESC
        """
        cursor.execute(query, (session['user_id'],))
        tickets = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Formatting data before sending to frontend
        for t in tickets:
            # Format Departure Date/Time
            if t.get('departure_time'):
                t['date'] = t['departure_time'].strftime("%d %b %Y")
                t['time'] = t['departure_time'].strftime("%I:%M %p")
            else:
                t['date'] = 'Pending'
                t['time'] = 'Pending'
                
            # FIX 2: Format Booking Date properly for JavaScript
            if t.get('booking_date'):
                t['booking_date'] = t['booking_date'].strftime("%Y-%m-%dT%H:%M:%S")
            else:
                t['booking_date'] = None
                
        return jsonify(tickets)
        
    except Exception as e:
        print(f"Booking Fetch Error: {str(e)}")
        return jsonify([])
    
    
# 3. Cancel a booking
@app.route('/api/cancel_booking', methods=['POST'])
def cancel_booking():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    data = request.json
    booking_id = data['booking_id']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Delete the booking from the database
    cursor.execute("DELETE FROM bookings WHERE id = %s AND user_id = %s", (booking_id, session['user_id']))
    conn.commit()
    
    cursor.close()
    conn.close()
    return jsonify({"success": True, "message": "Booking cancelled successfully."})

def generate_pnr():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# --- API: BOOK A FLIGHT (WITH SMART SEAT ASSIGNMENT) ---
@app.route('/api/book_flight', methods=['POST'])
def book_flight():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    data = request.json
    flight_id = data.get('flight_id')
    seat_pref = data.get('seat_pref', 'any').lower() # Get user's preference
    
    pnr = generate_pnr()
    
    # 🧠 SMART SEAT RECOMMENDATION LOGIC
    row = random.randint(1, 30) # Front to back rows
    
    if seat_pref == 'window':
        col = random.choice(['A', 'F'])
    elif seat_pref == 'aisle':
        col = random.choice(['C', 'D'])
    elif seat_pref == 'middle':
        col = random.choice(['B', 'E'])
    else:
        col = random.choice(['A', 'B', 'C', 'D', 'E', 'F']) # Any seat
        
    seat = f"{row}{col}" # Example: 12A or 18F
    gate = f"T{random.randint(1,3)}-{random.randint(10, 50)}"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO bookings (user_id, flight_id, pnr, seat_number, gate) VALUES (%s, %s, %s, %s, %s)",
            (session['user_id'], flight_id, pnr, seat, gate)
        )
        conn.commit()
        return jsonify({"success": True, "message": f"Payment Successful! AI Assigned Seat: {seat}", "pnr": pnr})
    except Exception as e:
        print(f"Booking Error: {e}")
        return jsonify({"success": False, "message": "Booking failed due to server error."})
    finally:
        cursor.close()
        conn.close()

        # --- OTP SYSTEM ---
@app.route('/api/send_otp', methods=['POST'])
def send_otp():
    data = request.json
    phone = data.get('phone', '').strip()

    # Check if phone exists
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE phone = %s", (phone,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user:
         return jsonify({"success": False, "message": "Phone number not found. Please register."}), 404

    # Generate a 6-digit OTP
    otp = str(random.randint(100000, 999999))

    # Temporarily store the OTP in the server session
    session['temp_otp'] = otp
    session['temp_phone'] = phone

    # SIMULATE SENDING SMS (Prints to your VS Code Terminal!)
    print("\n" + "="*50)
    print(f"✈️ MOCK SMS SENT TO: {phone}")
    print(f"🔑 YOUR SKYNEST LOGIN OTP IS: {otp}")
    print("="*50 + "\n")

    return jsonify({"success": True, "message": "OTP sent! Check your terminal."})

@app.route('/api/verify_otp', methods=['POST'])
def verify_otp():
    data = request.json
    user_otp = data.get('otp', '').strip()

    # Check if the OTP matches what we saved in the session
    if 'temp_otp' in session and session['temp_otp'] == user_otp:
        # Log them in!
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE phone = %s", (session['temp_phone'],))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        session['user_id'] = user['id']
        session['user_name'] = user['full_name']
        session['user_role'] = user['role']

        # Clean up temp session variables
        session.pop('temp_otp', None)
        session.pop('temp_phone', None)

        return jsonify({"success": True, "message": "OTP Verified!", "redirect": "/"})
    else:
        return jsonify({"success": False, "message": "Invalid OTP. Please try again."}), 401
    
    # ==========================================
# --- ADMIN DASHBOARD ROUTES ---
# ==========================================

@app.route('/admin')
def admin_dashboard():
    # SECURITY: Kick them out if they aren't an admin
    if session.get('user_role') != 'admin':
        return redirect('/')
    return render_template('admin.html')

@app.route('/api/admin/stats', methods=['GET'])
def admin_stats():
    if session.get('user_role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Count total registered users (excluding admins)
    cursor.execute("SELECT COUNT(*) as total_users FROM users WHERE role != 'admin'")
    users = cursor.fetchone()
    
    # Count total flights active in the database
    cursor.execute("SELECT COUNT(*) as total_flights FROM flights")
    flights = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    # Returning dynamic stats and simulating a revenue number for the dashboard
    return jsonify({
        "total_users": users['total_users'],
        "total_flights": flights['total_flights'],
        "revenue": "₹ 4,25,800" 
    })

@app.route('/api/admin/add_flight', methods=['POST'])
def admin_add_flight():
    if session.get('user_role') != 'admin': 
        return jsonify({"success": False, "message": "Unauthorized"}), 403
        
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO flights (flight_number, origin, destination, departure_time, price, status) VALUES (%s, %s, %s, %s, %s, %s)",
            (data['flight_number'], data['origin'], data['destination'], data['departure_time'], data['price'], 'On Time')
        )
        conn.commit()
        return jsonify({"success": True, "message": "Flight Added Successfully!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/api/admin/update_status', methods=['POST'])
def update_status():
    if session.get('user_role') != 'admin': 
        return jsonify({"success": False, "message": "Unauthorized"}), 403
        
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE flights SET status = %s WHERE id = %s", (data['status'], data['flight_id']))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    return jsonify({"success": True, "message": "Flight Status Updated!"})


# ==========================================
# --- REAL AI CHATBOT ROUTE (GEMINI API) ---
# ==========================================

# Initialize the new client with your API key
client = genai.Client(api_key="AIzaSyAggNMzlLZdVWjYms91p4TiTgexMALgZ_E") 

bot_personality = """
You are SkyBot, a highly polite and smart AI travel assistant for a flight booking website called 'SkyNest'. 
Your job is to help users with:
1. Flight bookings and ticket cancellations.
2. Checking weather for destinations.
3. Flight delay predictions.
Keep your answers under 3 sentences. Be concise, helpful, and use emojis. 
If a user asks something completely unrelated to travel or flights, politely decline and steer them back to SkyNest services.
"""

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_msg = data.get('message', '')
    
    if not user_msg:
        return jsonify({"reply": "Please ask me a question!"})

    try:
        # ATTEMPT 1: Try the Real Gemini AI
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_msg,
            config=types.GenerateContentConfig(
                system_instruction=bot_personality,
            )
        )
        return jsonify({"reply": response.text})
        
    except Exception as e:
        # ATTEMPT 2: If Google API fails (503), SILENTLY use Fallback Logic!
        print(f"⚠️ API Busy, using Fallback Bot. Error: {e}")
        
        msg_lower = user_msg.lower()
        if 'weather' in msg_lower:
            reply = "⛅ The weather at most of our top destinations (like Goa & Delhi) is sunny today! All flights are on schedule."
        elif 'book' in msg_lower or 'ticket' in msg_lower:
            reply = "🎟️ To book a flight, close this chat, scroll down to the 'Live Flight Board', and click the blue 'Reserve Now' button!"
        elif 'cancel' in msg_lower or 'refund' in msg_lower:
            reply = "❌ Need to cancel? Go to 'My Trips' (Profile) from the top navigation bar and click the red 'Cancel Flight' button."
        elif 'delay' in msg_lower or 'status' in msg_lower:
            reply = "⏱️ Click the '✨ Ask AI Delay Predictor' button on any flight card to check its status!"
        elif 'hello' in msg_lower or 'hi' in msg_lower or 'hey' in msg_lower:
            reply = "👋 Hello! I am SkyBot. Ask me about weather, booking tickets, or flight delays!"
        else:
            reply = "🤖 (slow Internet connectivity) I am currently handling simple queries. Try asking: 'How do I book a ticket?' or 'What is the weather?'"
            
        time.sleep(1) # Simulate real AI typing delay
        return jsonify({"reply": reply})
    
    

# --- START THE SERVER ---
if __name__ == '__main__':
    app.run(debug=True, port=5001)
    