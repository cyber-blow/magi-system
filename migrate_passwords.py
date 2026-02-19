import json
import os
import bcrypt

USERS_PATH = os.path.join(os.path.dirname(__file__), "users.json")

def load_json(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def migrate_passwords():
    print(f"Reading from {USERS_PATH}...")
    data = load_json(USERS_PATH)
    users = data.get("users", {})
    
    updated_count = 0
    for username, info in users.items():
        password = info.get("password", "")
        # Check if already hashed (bcrypt usually starts with $2b$, $2a$, or $2y$)
        if not password.startswith("$2b$"):
            print(f"Hashing password for user: {username}")
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            users[username]["password"] = hashed
            updated_count += 1
        else:
            print(f"User {username} already has hashed password.")
            
    if updated_count > 0:
        data["users"] = users
        save_json(USERS_PATH, data)
        print(f"Successfully migrated {updated_count} users.")
    else:
        print("No users needed migration.")

if __name__ == "__main__":
    migrate_passwords()
