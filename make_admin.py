from app import get_db_connection

print("🚀 Hacking the Database... Forcing Admin Roles!")

try:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Ye line database ke HAR user ko pakad kar Admin bana degi!
    cursor.execute("UPDATE users SET role = 'admin'")
    conn.commit() # Save changes permanently
    
    print("✅ SUCCESS! Database completely overridden. You are now an Admin.")
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f"❌ ERROR: {e}")