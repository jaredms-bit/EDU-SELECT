import requests
import json
import time
import subprocess
import sys

def test_admin():
    print("Starting admin test...")
    
    # Start server in background
    proc = subprocess.Popen([sys.executable, 'app.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(5) # Wait for server to start

    try:
        # 1. Get All Records
        print("Fetching all records...")
        res = requests.get('http://127.0.0.1:5000/api/records')
        if res.status_code != 200:
            print(f"Failed to get records: {res.text}")
            return
        records = res.json()
        print(f"Got {len(records)} records.")
        
        if not records:
            print("No records to test update/delete.")
            return

        target_id = records[-1]['ID']
        print(f"Testing with Record ID: {target_id}")

        # 2. Update Record
        print("Updating record...")
        update_data = {"Nombre": "Updated Name"}
        res = requests.put(f'http://127.0.0.1:5000/api/records/{target_id}', json=update_data)
        if res.status_code == 200:
            print("Update successful.")
        else:
            print(f"Update failed: {res.text}")

        # 3. Verify Update
        res = requests.get('http://127.0.0.1:5000/api/records')
        updated_records = res.json()
        updated_record = next((r for r in updated_records if r['ID'] == target_id), None)
        if updated_record and updated_record['Nombre'] == "Updated Name":
            print("Update verified.")
        else:
            print("Update verification failed.")

        # 4. Delete Record
        print("Deleting record...")
        res = requests.delete(f'http://127.0.0.1:5000/api/records/{target_id}')
        if res.status_code == 200:
            print("Delete successful.")
        else:
            print(f"Delete failed: {res.text}")

        # 5. Verify Delete
        res = requests.get('http://127.0.0.1:5000/api/records')
        final_records = res.json()
        if not any(r['ID'] == target_id for r in final_records):
            print("Delete verified.")
        else:
            print("Delete verification failed.")

    except Exception as e:
        print(f"Test failed with exception: {e}")
    finally:
        proc.terminate()
        print("Server terminated.")

if __name__ == "__main__":
    test_admin()
