import os
import sys
from dotenv import load_dotenv
from PyViCare.PyViCare import PyViCare
import json

# Load environment variables
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, ".env")
load_dotenv(env_path)

USER = os.getenv("VIESSMANN_USER", "")
PASSWORD = os.getenv("VIESSMANN_PASSWORD", "")
CLIENT_ID = os.getenv("VIESSMANN_CLIENT_ID", "")

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


def get_value_from_dump(dump_data, feature_name, property_name):
    for feature in dump_data:
        if feature["feature"] == feature_name:
            if property_name in feature["properties"]:
                return feature["properties"][property_name]["value"]
    return None


def verify_batch_fetch(device):
    print("\n--- Verifying Batch Fetch (Single API Call) ---")
    try:
        # 1. Fetch all features (ONE API CALL)
        print("Fetching all features...")
        dump = device.service.fetch_all_features()
        data = dump["data"]
        print(f"Fetched {len(data)} features.")

        # 2. Extract Metrics locally
        print("\n[Metrics Extraction]")

        # Outside Temp
        val = get_value_from_dump(data, "heating.sensors.temperature.outside", "value")
        print(f"Outside Temp: {val}")

        # Return Temp
        val = get_value_from_dump(data, "heating.sensors.temperature.return", "value")
        print(f"Return Temp: {val}")

        # Supply Temp (Circuit 0)
        val = get_value_from_dump(data, "heating.circuits.0.sensors.temperature.supply", "value")
        print(f"Supply Temp (Circuit 0): {val}")

        # Supply Temp (Circuit 1)
        val = get_value_from_dump(data, "heating.circuits.1.sensors.temperature.supply", "value")
        print(f"Supply Temp (Circuit 1): {val}")

        # Circuit 0 Pump
        val = get_value_from_dump(data, "heating.circuits.0.circulation.pump", "status")
        print(f"Circuit 0 Pump: {val}")

        # Circuit 1 Pump
        val = get_value_from_dump(data, "heating.circuits.1.circulation.pump", "status")
        print(f"Circuit 1 Pump: {val}")

        # Compressor Power (Rated)
        val = get_value_from_dump(data, "heating.compressors.0.power", "value")
        print(f"Compressor Rated Power: {val}")

        # Compressor Modulation
        val = get_value_from_dump(data, "heating.compressors.0.sensors.power", "value")
        print(f"Compressor Modulation: {val}")

        # Compressor Runtime (Hours)
        val = get_value_from_dump(data, "heating.compressors.0.statistics", "hours")
        print(f"Compressor Runtime (Hours): {val}")

        # DHW Storage Temp
        val = get_value_from_dump(data, "heating.dhw.sensors.temperature.hotWaterStorage", "value")
        print(f"DHW Storage Temp: {val}")

        # Circulation Pump Status
        val = get_value_from_dump(data, "heating.dhw.pumps.circulation", "status")
        print(f"Circulation Pump: {val}")

    except Exception as e:
        print(f"Batch fetch failed: {e}")


def main():
    print("Connecting to Viessmann API...")
    try:
        vicare = PyViCare()
        token_file = os.path.join(script_dir, "token.save")
        vicare.initWithCredentials(username=USER, password=PASSWORD, client_id=CLIENT_ID, token_file=token_file)

        print(f"Found {len(vicare.devices)} devices/components:")
        target_device = None

        for i, dev in enumerate(vicare.devices):
            print(f"  [{i}] Model: {dev.getModel()}, Status: {dev.isOnline()}")
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
        dump_file = os.path.join(script_dir, "viessmann_dump.json")
        with open(dump_file, "w") as f:
            json.dump(dump, f, indent=2)
        print(f"Saved feature dump to '{dump_file}'.")
    except Exception as e:
        print(f"Failed to dump features: {e}")

    # 1. Outside Temperature
    check_feature("Outside Temperature", lambda: device.getOutsideTemperature())

    # 2. Supply Temperature
    try:
        circuit = device.circuits[0]
        check_feature("Supply Temperature (Circuit 0)", lambda: circuit.getSupplyTemperature())
    except IndexError:
        print("[MISSING] No heating circuits found.")
    except Exception as e:
        print(f"[MISSING] Supply Temperature: {e}")

    # 3. Return Temperature
    check_feature("Return Temperature", lambda: device.getReturnTemperature())

    # 4. Current Heat Production
    check_feature(
        "Compressor 0 Power (Thermal?)", lambda: device.service.getProperty("heating.compressors.0.power")["properties"]["value"]["value"]
    )
    check_feature(
        "Compressor 0 Modulation", lambda: device.service.getProperty("heating.compressors.0.sensors.power")["properties"]["value"]["value"]
    )

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

            # Supply Temp (if available per circuit)
            check_feature(f"Circuit {i} Supply Temp", lambda: circuit.getSupplyTemperature())

            # Pump Status (Corrected Feature Name)
            check_feature(
                f"Circuit {i} Pump Status",
                lambda: device.service.getProperty(f"heating.circuits.{i}.circulation.pump")["properties"]["status"]["value"],
            )

    except Exception as e:
        print(f"[MISSING] Circuit Data: {e}")

    # 7. Domestic Hot Water (DHW)
    print("\n--- Checking Domestic Hot Water (DHW) ---")
    try:
        check_feature("DHW Schedule", lambda: device.getDomesticHotWaterSchedule())
        check_feature("DHW Target Temp (Configured)", lambda: device.getDomesticHotWaterDesiredTemperature())
        check_feature("DHW Storage Temp", lambda: device.getDomesticHotWaterStorageTemperature())
    except Exception as e:
        print(f"[MISSING] DHW Data: {e}")

    # 8. Circulation Pump (DHW)
    print("\n--- Checking Circulation Pump ---")
    try:
        check_feature(
            "Circulation Pump Active", lambda: device.service.getProperty("heating.dhw.pumps.circulation")["properties"]["status"]["value"]
        )
    except Exception as e:
        print(f"[MISSING] Circulation Pump Data: {e}")

    # Verify batch fetch
    verify_batch_fetch(device)

    print("\n--- Verification Complete ---")


if __name__ == "__main__":
    main()
