import json
import os

DB_FILE = "user_db.json"

if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        USER_DB = json.load(f)
else:
    USER_DB = {}

def save_user(chat_id, name, resolution, plan=None, phase="intake", reminder_time=None):
    """Saves user data including the specific Reminder Time."""
    # Preserve existing data if updating
    current = USER_DB.get(str(chat_id), {})
    
    # LOGIC: If a new reminder_time is passed, use it. Otherwise, keep the old one.
    final_time = reminder_time if reminder_time else current.get("reminder_time")

    USER_DB[str(chat_id)] = {
        "name": name,
        "resolution": resolution,
        "plan": plan or current.get("plan"),
        "phase": phase,
        "reminder_time": final_time  # <--- THIS WAS MISSING IN YOUR CODE
    }
    
    with open(DB_FILE, "w") as f:
        json.dump(USER_DB, f)
    
    # Debug print to confirm it saved
    print(f"💾 Saved {name}: Phase={phase}, Time={final_time}")

def get_user(chat_id):
    return USER_DB.get(str(chat_id))

def get_all_users():
    return USER_DB