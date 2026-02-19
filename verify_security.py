import magi_core
import os

def test_security():
    print("--- Testing Security Implementation ---")
    
    # 1. Test Env Vars
    print("\n1. Testing API Key Loading...")
    config = magi_core.load_api_config()
    google_key = config["providers"]["google"]["api_key"]
    if google_key and not google_key.startswith("AIza"):
        print(f"[FAIL] Google API Key appears invalid or missing: {google_key[:5]}...")
    elif google_key:
        print(f"[PASS] Google API Key loaded: {google_key[:5]}...")
    else:
        print("[FAIL] Google API Key NOT loaded.")
        
    # 2. Test Login
    print("\n2. Testing Login (bcrypt)...")
    # user: nerv_admin, pass: nerv
    user = magi_core.authenticate_user("nerv_admin", "nerv")
    if user:
        print(f"[PASS] Authentication successful for 'nerv_admin'. Role: {user['role']}")
    else:
        print("[FAIL] Authentication failed for 'nerv_admin' with correct password.")
        
    # Test wrong password
    user_fail = magi_core.authenticate_user("nerv_admin", "wrong_pass")
    if not user_fail:
        print("[PASS] Authentication rejected for wrong password.")
    else:
        print("[FAIL] Authentication succeded with WRONG password!")

if __name__ == "__main__":
    test_security()
