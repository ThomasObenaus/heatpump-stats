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
    print("\n--- Checking Heating Circuits ---")
    try:
        circuits = device.circuits
        print(f"Found {len(circuits)} heating circuits.")
        
        for i, circuit in enumerate(circuits):
            print(f"\n[Circuit {i}]")
            # Schedule
            check_feature(f"Circuit {i} Schedule", lambda: circuit.getHeatingSchedule())
            
            # Target Temperatures
            check_feature(f"Circuit {i} Target Temp (Current)", lambda: circuit.getCurrentDesiredTemperature())
            check_feature(f"Circuit {i} Target Temp (Comfort)", lambda: circuit.getDesiredTemperatureForProgram("comfort"))
            check_feature(f"Circuit {i} Target Temp (Normal)", lambda: circuit.getDesiredTemperatureForProgram("normal"))
            check_feature(f"Circuit {i} Target Temp (Reduced)", lambda: circuit.getDesiredTemperatureForProgram("reduced"))
            
            # Supply Temp (if available per circuit)
            check_feature(f"Circuit {i} Supply Temp", lambda: circuit.getSupplyTemperature())

    except Exception as e:
        print(f"[MISSING] Circuit Data: {e}")

    # 6. Target Temperature (Legacy check removed)
    
    # 7. Domestic Hot Water (DHW)
    print("\n--- Checking Domestic Hot Water (DHW) ---")
    try:
        # Schedule
        check_feature("DHW Schedule", lambda: device.getDomesticHotWaterSchedule())
        
        # Target Temperature
        check_feature("DHW Target Temp (Configured)", lambda: device.getDomesticHotWaterDesiredTemperature())
        
        # Supply Temperature (Storage Temp)
        check_feature("DHW Storage Temp", lambda: device.getDomesticHotWaterStorageTemperature())
        
        # Check for specific DHW circuits if applicable (usually just one global DHW setting)
        
    except Exception as e:
        print(f"[MISSING] DHW Data: {e}")

    # 8. Circulation Pump (DHW)
    print("\n--- Checking Circulation Pump ---")
    try:
        # Schedule - The method name might be different or it might be a property
        # Let's try to find it via the feature name directly if the method doesn't exist
        check_feature("Circulation Pump Schedule", lambda: device.service.getProperty("heating.dhw.pumps.circulation.schedule")["properties"]["entries"]["value"])
        
        # Status
        check_feature("Circulation Pump Active", lambda: device.service.getProperty("heating.dhw.pumps.circulation")["properties"]["status"]["value"])
        
    except Exception as e:
        print(f"[MISSING] Circulation Pump Data: {e}")

    # 9. Power Consumption (Heating) - Just to see if we have it
    check_feature("Power Consumption Summary (Heating, Today)", lambda: device.getPowerSummaryConsumptionHeatingCurrentDay())

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    main()
