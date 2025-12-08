import requests
import sys
import time
import os

# Force some encoding handling if needed, but easier to just use ASCII
sys.stdout.reconfigure(encoding='utf-8')

def test_endpoints():
    base_url = "http://127.0.0.1:5000"
    
    print("[INFO] Wait for server startup...")
    time.sleep(2) 

    # 1. Test Home Page
    try:
        print(f"[INFO] Testing connectivity to {base_url}...")
        resp = requests.get(base_url)
        if resp.status_code == 200:
            print("[SUCCESS] Home page accessible.")
        else:
            print(f"[FAILURE] Home page returned status code: {resp.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"[FAILURE] Failed to connect to home page: {e}")
        sys.exit(1)

    # 2. Test Admin Records API (Tests DB connection)
    try:
        print(f"[INFO] Testing DB connection via {base_url}/api/records...")
        resp = requests.get(f"{base_url}/api/records")
        if resp.status_code == 200:
            print("[SUCCESS] Database connection successful.")
            print("Records:", resp.json())
        else:
            print(f"[FAILURE] API returned status code: {resp.status_code}")
            print("Response:", resp.text)
            if resp.status_code == 500:
                print("[WARNING] This likely means MongoDB is not running or not accessible.")
            sys.exit(1)
    except Exception as e:
        print(f"[FAILURE] Failed to connect to API: {e}")
        sys.exit(1)

    print("\n[SUCCESS] All checks passed!")

if __name__ == "__main__":
    test_endpoints()
