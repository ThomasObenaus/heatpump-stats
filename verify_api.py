import os
import sys
from dotenv import load_dotenv
from PyViCare.PyViCareService import PyViCareService
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
        device = vicare.devices[0] # Get the first device
        print(f"Connected to device: {device.getModel()} (Status: {device.isOnline()})")
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)

    print("\n--- Verifying Required Data Points ---")

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
    # This is usually on the compressor.
    try:
        compressors = device.compressors
        if compressors:
            compressor = compressors[0]
            check_feature("Current Heat Production (Compressor 0)", lambda: compressor.getHeatProductionCurrent())
            check_feature("Compressor Active", lambda: compressor.isActive())
        else:
            print("[MISSING] No compressors found.")
    except Exception as e:
        print(f"[MISSING] Compressor Data: {e}")

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
