import os
import sys
import logging
import json
from unittest.mock import MagicMock
from PyViCare.PyViCare import PyViCare
from PyViCare.PyViCareAbstractOAuthManager import AbstractViCareOAuthManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_caching")

class MockOAuthManager(AbstractViCareOAuthManager):
    def __init__(self):
        self.call_count = 0
        self.urls_called = []

    def get(self, url):
        self.call_count += 1
        self.urls_called.append(url)
        print(f"  -> [MOCK NETWORK] GET {url}")
        
        if "installations" in url and "features" not in url:
            # Initial discovery
            return {
                "data": [{
                    "id": 12345,
                    "gateways": [{
                        "serial": "1234567890123456",
                        "devices": [{
                            "id": "0",
                            "modelId": "CU401B_G",
                            "status": "online",
                            "deviceType": "heating",
                            "roles": ["type:heatpump"]
                        }]
                    }]
                }]
            }
        
        if "features" in url:
            # Feature fetch
            return {
                "data": [
                    {
                        "feature": "heating.sensors.temperature.outside",
                        "properties": {
                            "value": { "value": 5.5 }
                        }
                    },
                    {
                        "feature": "heating.sensors.temperature.return",
                        "properties": {
                            "value": { "value": 28.0 }
                        }
                    },
                    {
                        "feature": "heating.dhw.sensors.temperature.hotWaterStorage",
                        "properties": {
                            "value": { "value": 45.0 }
                        }
                    },
                    {
                        "feature": "heating.circuits.0.sensors.temperature.supply",
                        "properties": {
                            "value": { "value": 32.0 }
                        }
                    }
                ]
            }
        
        print(f"  -> [MOCK NETWORK] WARNING: Unhandled URL: {url}")
        return {}

    def post(self, url, data):
        pass

    def renewToken(self):
        pass

def main():
    print("--- Viessmann Caching Verification (Mocked Network) ---")
    print("This script uses the real PyViCare library logic but mocks the network layer.")
    print("It proves that the library caches data automatically on the first property access.\n")

    # 1. Setup PyViCare with Mock OAuth
    vicare = PyViCare()
    mock_oauth = MockOAuthManager()
    
    # Initialize with our mock (bypassing real auth)
    print("1. Initializing PyViCare with Mock OAuthManager...")
    vicare.initWithExternalOAuth(mock_oauth)
    
    # Get the device config
    device_config = vicare.devices[0]
    print(f"   Connected to device: {device_config.getModel()}")
    
    # Get the HeatPump object
    device = device_config.asHeatPump()
    
    # Reset counters after initialization (init calls installations endpoint)
    print(f"   (Initialization made {mock_oauth.call_count} network calls)")
    mock_oauth.call_count = 0
    mock_oauth.urls_called = []

    print("\n2. Accessing properties...")
    print("   We expect the FIRST access to trigger a network call, and subsequent ones to use the cache.")
    
    print("   - getOutsideTemperature()")
    try:
        val = device.getOutsideTemperature()
        print(f"     Value: {val}")
    except Exception as e:
        print(f"     Error: {e}")

    print("   - getReturnTemperature()")
    try:
        val = device.getReturnTemperature()
        print(f"     Value: {val}")
    except Exception as e:
        print(f"     Error: {e}")

    print("   - getDomesticHotWaterStorageTemperature()")
    try:
        val = device.getDomesticHotWaterStorageTemperature()
        print(f"     Value: {val}")
    except Exception as e:
        print(f"     Error: {e}")

    final_count = mock_oauth.call_count
    
    print(f"\n--- RESULTS ---")
    print(f"Total Network Calls during property access: {final_count}")
    
    if final_count == 1:
        print("SUCCESS: Exactly one network call was made for multiple property accesses.")
        print("This confirms that PyViCare caches the data automatically.")
    else:
        print(f"FAILURE: Expected 1 call, but got {final_count}.")

if __name__ == "__main__":
    main()
