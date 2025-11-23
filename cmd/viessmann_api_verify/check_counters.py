import os
import sys
import json
from dotenv import load_dotenv
from PyViCare.PyViCare import PyViCare

# Load environment variables
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env')
load_dotenv(env_path)

USER = os.getenv("VIESSMANN_USER")
PASSWORD = os.getenv("VIESSMANN_PASSWORD")
CLIENT_ID = os.getenv("VIESSMANN_CLIENT_ID")

if not all([USER, PASSWORD, CLIENT_ID]):
    print("Error: Missing credentials in .env file.")
    sys.exit(1)

# Type assertion for mypy/linters
assert USER is not None
assert PASSWORD is not None
assert CLIENT_ID is not None

def main():
    print("Connecting to Viessmann API...")
    try:
        vicare = PyViCare()
        token_file = os.path.join(script_dir, "token.save")
        vicare.initWithCredentials(USER, PASSWORD, CLIENT_ID, token_file)
        
        target_device = None
        for dev in vicare.devices:
            print(f"Found Device: {dev.getModel()}")
            if "Heatbox" not in dev.getModel() and "Vitoconnect" not in dev.getModel():
                target_device = dev
                break
        
        if not target_device:
            print("Error: Could not find a heating device (skipping Gateways).")
            # Fallback to first device if nothing else found, just in case
            target_device = vicare.devices[0]

        print(f"Selected Device: {target_device.getModel()}")

        print("Fetching all features...")
        dump = target_device.service.fetch_all_features()
        data = dump["data"]
        
        print(f"Scanning {len(data)} features for counters...")
        
        keywords = ["statistics", "hours", "starts", "energy", "consumption", "operating", "counter"]
        found_counters = []

        for feature in data:
            name = feature["feature"]
            if any(k in name.lower() for k in keywords):
                found_counters.append(feature)

        if found_counters:
            print(f"\nFound {len(found_counters)} potential counter features:")
            for f in found_counters:
                print(f"\nFeature: {f['feature']}")
                print(f"Properties: {json.dumps(f['properties'], indent=2)}")
        else:
            print("\nNo obvious counter features found.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
