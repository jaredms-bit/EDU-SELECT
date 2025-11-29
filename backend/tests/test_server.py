import requests
import json
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5, AES
from Crypto.Util.Padding import pad
from Crypto.Random import get_random_bytes
import base64
import time
import subprocess
import sys

def test_backend():
    print("Starting backend test...")
    
    # Start server in background
    proc = subprocess.Popen([sys.executable, 'app.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(5) # Wait for server to start

    try:
        # 1. Get Public Key
        print("Fetching public key...")
        try:
            res = requests.get('http://127.0.0.1:5000/public-key')
        except requests.exceptions.ConnectionError:
            print("Failed to connect to server. Is it running?")
            return

        if res.status_code != 200:
            print(f"Failed to get public key: {res.text}")
            return
        
        public_key_pem = res.json()['publicKey']
        public_key = RSA.import_key(public_key_pem)
        cipher_rsa = PKCS1_v1_5.new(public_key)
        print("Public key received.")

        # 2. Encrypt Data (Hybrid)
        data = {
            "Nombre": "Test User",
            "Nivel Educativo": "Test Level",
            "Institución": "Test Inst",
            "Experiencia (años)": "5",
            "Tipo": "Test"
        }
        json_data = json.dumps(data)
        
        # A. Generate AES Key
        aes_key = get_random_bytes(32) # 256 bits
        aes_key_b64 = base64.b64encode(aes_key).decode('utf-8')
        
        # B. Encrypt AES Key with RSA
        # JS encrypts the Base64 string of the key
        encrypted_key = cipher_rsa.encrypt(aes_key_b64.encode('utf-8'))
        encrypted_key_b64 = base64.b64encode(encrypted_key).decode('utf-8')
        
        # C. Encrypt Data with AES-GCM
        iv = get_random_bytes(12)
        cipher_aes = AES.new(aes_key, AES.MODE_GCM, nonce=iv)
        encrypted_data, tag = cipher_aes.encrypt_and_digest(json_data.encode('utf-8'))
        
        # Combine ciphertext and tag? JS WebCrypto usually returns them combined if using 'AES-GCM'.
        # But wait, in app.py I did: tag = encrypted_data[-16:]
        # So I should append tag to ciphertext here.
        full_encrypted_data = encrypted_data + tag
        encrypted_data_b64 = base64.b64encode(full_encrypted_data).decode('utf-8')
        iv_b64 = base64.b64encode(iv).decode('utf-8')
        
        print("Data encrypted.")

        # 3. Send to Register
        print("Sending registration...")
        payload = {
            'key': encrypted_key_b64,
            'iv': iv_b64,
            'data': encrypted_data_b64
        }
        res = requests.post('http://127.0.0.1:5000/register', json=payload)
        
        if res.status_code == 200:
            print(f"Registration successful: {res.json()}")
        else:
            print(f"Registration failed: {res.text}")

    except Exception as e:
        print(f"Test failed with exception: {e}")
    finally:
        proc.terminate()
        print("Server terminated.")

if __name__ == "__main__":
    test_backend()
