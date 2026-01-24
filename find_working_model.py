import vertexai
from vertexai.generative_models import GenerativeModel
from dotenv import load_dotenv
import os

load_dotenv()

# 1. Your Project ID
PROJECT_ID = "gen-lang-client-0633619694"

# 2. The Combinations we will test
REGIONS = ["us-central1", "us-west1", "us-east4", "northamerica-northeast1", "us-east1"]
MODELS = [
    "gemini-1.5-flash-001",  # Most likely
    "gemini-1.5-flash",      # Alias
    "gemini-1.5-pro-001",    # Stronger
    "gemini-1.0-pro-001",    # Older/Stable
    "gemini-pro"             # Oldest Alias
]

print(f"🚀 Starting Scanner for Project: {PROJECT_ID}")
print("------------------------------------------------")

found_winner = False

for region in REGIONS:
    if found_winner: break
    
    print(f"\n🌍 Checking Region: {region}...")
    try:
        # Initialize the Cloud Connection for this region
        vertexai.init(project=PROJECT_ID, location=region)
    except Exception as e:
        print(f"   Constructor failed for {region}")
        continue

    for model_name in MODELS:
        print(f"   👉 Testing Model: {model_name}...", end=" ")
        try:
            # Try to load and run the model
            model = GenerativeModel(model_name)
            response = model.generate_content("Say 'Success' if you can hear me.")
            
            # IF WE GET HERE, IT WORKED!
            print("✅ SUCCESS!")
            print("\n🎉 WINNER FOUND! 🎉")
            print(f"Use this in main.py:")
            print(f'LOCATION = "{region}"')
            print(f'model = GenerativeModel("{model_name}")')
            found_winner = True
            break
        except Exception as e:
            # If it fails, just print a small x and keep going
            error_msg = str(e)
            if "404" in error_msg:
                print("❌ (Not Found)")
            elif "403" in error_msg:
                print("🔒 (Permission Denied)")
            else:
                print(f"⚠️ ({error_msg[:20]}...)")

if not found_winner:
    print("\n❌ Scanner finished. No working combination found.")
    print("This means the API is disabled or your account has absolutely no access.")