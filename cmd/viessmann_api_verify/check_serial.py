import os
import sys
from dotenv import load_dotenv
from PyViCare.PyViCare import PyViCare

# Load environment variables
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env')
load_dotenv(env_path)

USER = os.getenv("VIESSMANN_USER", "")
PASSWORD = os.getenv("VIESSMANN_PASSWORD","")
CLIENT_ID = os.getenv("VIESSMANN_CLIENT_ID","")

def main():
    print("Connecting to Viessmann API...")
    try:
        vicare = PyViCare()
        token_file = os.path.join(script_dir, "token.save")
        vicare.initWithCredentials(username=USER, password=PASSWORD, client_id=CLIENT_ID, token_file=token_file)
        
        print(f"Found {len(vicare.devices)} devices.")
        for i, dev in enumerate(vicare.devices):
            print(f"Device {i}: Model={dev.getModel()}, ID={dev.service.accessor.id}")

        target_device = None
        for dev in vicare.devices:
            if "Heatbox" not in dev.getModel() and "Vitoconnect" not in dev.getModel():
                target_device = dev
                break
        
        if not target_device:
            print("No suitable heat pump device found. Using first device.")
            target_device = vicare.devices[0]

        print(f"Selected Device Model: {target_device.getModel()}")
        
        device = target_device.asHeatPump()
        
        # Force fetch all features to debug
        print("Fetching all features...")
        features = device.service.fetch_all_features()
        print(f"Fetched {len(features['data'])} features.")
        
        print("\n--- Checking Serial Numbers ---")
        
        try:
            serial = device.getSerial()
            print(f"getSerial(): {serial}")
        except Exception as e:
            print(f"getSerial() failed: {type(e).__name__}: {e}")

        try:
            # Note: PyViCare might not have getControllerSerial exposed directly on HeatPump, 
            # but it maps to heating.controller.serial feature.
            # Let's check if the method exists first.
            if hasattr(device, "getControllerSerial"):
                serial = device.getControllerSerial()
                print(f"getControllerSerial(): {serial}")
            else:
                print("getControllerSerial() method not found on device object.")
                
        except Exception as e:
            print(f"getControllerSerial() failed: {type(e).__name__}: {e}")
            
        # Debug: Check features directly
        print("\n--- Feature Debug ---")
        for feature_name in ["device.serial", "heating.controller.serial", "heating.boiler.serial"]:
            try:
                prop = device.service.getProperty(feature_name)
                print(f"Feature '{feature_name}': {prop}")
            except Exception as e:
                print(f"Feature '{feature_name}' access failed: {e}")

        try:
            if hasattr(device, "getBoilerSerial"):
                serial = device.getBoilerSerial()
                print(f"getBoilerSerial(): {serial}")
            else:
                print("getBoilerSerial() method not found.")
        except Exception as e:
            print(f"getBoilerSerial() failed: {e}")

    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    main()
