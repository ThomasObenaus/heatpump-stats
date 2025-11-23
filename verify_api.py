import os
import sys
from dotenv import load_dotenv
from PyViCare.PyViCare import PyViCare

# Load environment variables
load_dotenv()

USER = os.getenv("VIESSMANN_USER")
PASSWORD = os.getenv("VIESSMANN_PASSWORD")
CLIENT_ID = os.getenv("VIESSMANN_CLIENT_ID")

if not all([USER, PASSWORD, CLIENT_ID]):
    print("Error: Missing credentials in .env file.")
    print("Please copy .env.example to .env and fill in your Viessmann credentials.")
    sys.exit(1)

def check_feature(name, func):
    try:
        value = func()
        print(f"[OK] {name}: {value}")
        return True
    except Exception as e:
        print(f"[MISSING] {name}: {e}")
        return False

def main():
    print("Connecting to Viessmann API...")
    try:
        vicare = PyViCare()
        vicare.initWithCredentials(USER, PASSWORD, CLIENT_ID, "token.save")
        
        print(f"Found {len(vicare.devices)} devices/components:")
        target_device = None
        
        for i, dev in enumerate(vicare.devices):
            print(f"  [{i}] Model: {dev.getModel()}, Status: {dev.isOnline()}")
            # We are looking for the heating device, usually ID 0, but let's check the model
            # The gateway is usually Heatbox... or Vitoconnect...
            # The heatpump is usually something else.
            if "Heatbox" not in dev.getModel() and "Vitoconnect" not in dev.getModel():
                 target_device = dev

        if target_device:
            print(f"\nSelected device: {target_device.getModel()}")
            device = target_device.asHeatPump()
        else:
            print("\nCould not identify a specific heating device. Using the first one.")
            device = vicare.devices[0].asHeatPump()

    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)

    print("\n--- Verifying Required Data Points ---")

    # Dump all data for debugging
    print("\n--- Dumping All Available Features ---")
    try:
        # This fetches the raw JSON data from the API
        dump = device.service.fetch_all_features()
        print(f"Total features found: {len(dump['data'])}")
        # Save to a file for inspection
        import json
        with open("viessmann_dump.json", "w") as f:
            json.dump(dump, f, indent=2)
        print("Saved feature dump to 'viessmann_dump.json'.")
    except Exception as e:
        print(f"Failed to dump features: {e}")

    # 1. Outside Temperature
    check_feature("Outside Temperature", lambda: device.getOutsideTemperature())

    # 2. Supply Temperature
    # Note: This might be on a specific circuit. We'll try the first circuit.
    try:
        circuit = device.circuits[0]
        check_feature("Supply Temperature (Circuit 0)", lambda: circuit.getSupplyTemperature())
    except IndexError:
        print("[MISSING] No heating circuits found.")
    except Exception as e:
        print(f"[MISSING] Supply Temperature: {e}")

    # 3. Return Temperature
    # Often not available on all devices, but good to check
    check_feature("Return Temperature", lambda: device.getReturnTemperature())

    # 4. Current Heat Production (Critical for JAZ)
    # We found 'heating.compressors.0.power' in the dump.
    check_feature("Compressor 0 Power (Thermal?)", lambda: device.service.getProperty("heating.compressors.0.power")["properties"]["value"]["value"])
    
    # Check modulation
    check_feature("Compressor 0 Modulation", lambda: device.service.getProperty("heating.compressors.0.sensors.power")["properties"]["value"]["value"])

    # 5. Heating Schedule
    try:
        circuit = device.circuits[0]
        check_feature("Heating Schedule", lambda: circuit.getHeatingSchedule())
    except:
        pass

    # 6. Target Temperature
    try:
        circuit = device.circuits[0]
        check_feature("Target Temperature", lambda: circuit.getCurrentDesiredTemperature())
    except:
        pass
    
    # 7. Power Consumption (Heating) - Just to see if we have it
    check_feature("Power Consumption Summary (Heating, Today)", lambda: device.getPowerSummaryConsumptionHeatingCurrentDay())

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    main()
