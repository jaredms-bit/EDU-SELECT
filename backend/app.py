from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5, AES
from Crypto.Util.Padding import unpad
import base64
import json
import os
import codigoia # Import the AI module

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# --- RSA Key Generation ---
# In a real app, you might load these from files.
# Here we generate them on startup for simplicity.
key = RSA.generate(2048)
private_key = key
public_key = key.publickey().export_key().decode('utf-8')
private_key_pem = key.export_key().decode('utf-8')

cipher_rsa = PKCS1_v1_5.new(private_key)

DB_FILE = 'base_del_proto.json'

# Train the model on startup
print("Entrenando modelo de IA...")
try:
    codigoia.train_model()
except Exception as e:
    print(f"Error entrenando modelo: {e}")

def load_db():
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading DB: {e}")
        return []

def save_db(data):
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving DB: {e}")

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/admin')
def admin():
    return send_from_directory('.', 'admin.html')

@app.route('/api/records', methods=['GET'])
def get_records():
    return jsonify(load_db())

@app.route('/api/records/<int:id>', methods=['PUT'])
def update_record(id):
    try:
        data = request.json
        db = load_db()
        for i, record in enumerate(db):
            if record.get('ID') == id:
                # Update fields
                db[i].update(data)
                save_db(db)
                return jsonify({'msg': 'Registro actualizado'}), 200
        return jsonify({'msg': 'Registro no encontrado'}), 404
    except Exception as e:
        print(f"Error updating record: {e}")
        return jsonify({'msg': 'Server error'}), 500

@app.route('/api/records/<int:id>', methods=['DELETE'])
def delete_record(id):
    try:
        db = load_db()
        new_db = [r for r in db if r.get('ID') != id]
        if len(new_db) == len(db):
            return jsonify({'msg': 'Registro no encontrado'}), 404
        save_db(new_db)
        return jsonify({'msg': 'Registro eliminado'}), 200
    except Exception as e:
        print(f"Error deleting record: {e}")
        return jsonify({'msg': 'Server error'}), 500

@app.route('/api/predict_all', methods=['POST'])
def predict_all():
    try:
        db = load_db()
        updated_count = 0
        for record in db:
            # Predict only if not present or force update (here we force update)
            prediction = codigoia.predict_candidate(record)
            record['Prediccion_IA'] = prediction
            updated_count += 1
        
        save_db(db)
        return jsonify({'msg': f'Predicciones generadas para {updated_count} registros', 'records': db}), 200
    except Exception as e:
        print(f"Error generating predictions: {e}")
        return jsonify({'msg': 'Server error generating predictions'}), 500

@app.route('/public-key', methods=['GET'])
def get_public_key():
    return jsonify({'publicKey': public_key})

@app.route('/register', methods=['POST'])
def register():
    try:
        req_data = request.json
        
        # Expecting: { "key": "encrypted_aes_key_b64", "iv": "iv_b64", "data": "encrypted_data_b64" }
        encrypted_key_b64 = req_data.get('key')
        iv_b64 = req_data.get('iv')
        encrypted_data_b64 = req_data.get('data')
        
        if not encrypted_key_b64 or not iv_b64 or not encrypted_data_b64:
            return jsonify({'msg': 'Missing encryption parameters'}), 400

        # 1. Decrypt AES Key with RSA
        try:
            encrypted_key = base64.b64decode(encrypted_key_b64)
            sentinel = None
            aes_key_b64_bytes = cipher_rsa.decrypt(encrypted_key, sentinel)
            if aes_key_b64_bytes is None:
                return jsonify({'msg': 'Key decryption failed'}), 400
            
            # The decrypted content is the Base64 string of the AES key (as bytes)
            aes_key = base64.b64decode(aes_key_b64_bytes)
            
        except Exception as e:
            print(f"Key decryption error: {e}")
            return jsonify({'msg': 'Key decryption error'}), 400

        # 2. Decrypt Data with AES
        try:
            iv = base64.b64decode(iv_b64)
            encrypted_data = base64.b64decode(encrypted_data_b64)
            
            # Using AES GCM (or CBC if GCM is too complex for simple JS lib, but WebCrypto supports GCM)
            # WebCrypto default is usually GCM. Let's assume GCM.
            # Note: PyCryptodome GCM requires the tag (MAC) to be separate or appended.
            # WebCrypto usually produces ciphertext + tag.
            # If using GCM, the tag is usually the last 16 bytes.
            
            cipher_aes = AES.new(aes_key, AES.MODE_GCM, nonce=iv)
            
            # Assuming the tag is appended to the end of the ciphertext (common in some libs, but WebCrypto returns it as part of the buffer? No, WebCrypto encrypt returns ciphertext which includes the tag at the end usually).
            # Let's try to split tag.
            tag = encrypted_data[-16:]
            ciphertext = encrypted_data[:-16]
            
            decrypted_data = cipher_aes.decrypt_and_verify(ciphertext, tag)
            
            # Parse decrypted JSON
            final_data = json.loads(decrypted_data.decode('utf-8'))
            
        except Exception as e:
            print(f"Data decryption error: {e}")
            return jsonify({'msg': 'Data decryption error'}), 400

        # Save to DB
        db = load_db()
        
        # Determine ID
        new_id = 1
        if db:
            # Assuming ID is numeric and unique
            ids = [item.get('ID', 0) for item in db]
            if ids:
                new_id = max(ids) + 1
        
        record = {}
        record['ID'] = new_id
        
        # Merge decrypted data into record
        record.update(final_data)
        
        # Generate prediction for new record
        try:
            prediction = codigoia.predict_candidate(record)
            record['Prediccion_IA'] = prediction
        except Exception as e:
            print(f"Error predicting for new record: {e}")
            record['Prediccion_IA'] = "Error"
        
        db.append(record)
        save_db(db)

        return jsonify({'msg': 'Registro exitoso', 'id': new_id}), 200

    except Exception as e:
        print(f"Server error: {e}")
        return jsonify({'msg': 'Server error'}), 500

if __name__ == '__main__':
    print("Starting Flask server on port 5000...")
    print(f"Database file: {os.path.abspath(DB_FILE)}")
    app.run(port=5000, debug=True)
