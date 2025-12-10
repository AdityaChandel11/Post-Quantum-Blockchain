# app.py
from flask import Flask, request, jsonify, render_template
from blockchain import Blockchain
from ecc_auth import NodeAuth
import json
import base64
import requests
import hashlib
from datetime import datetime
def canonical_json_str(obj):
    # deterministic JSON string
    return json.dumps(obj, sort_keys=True, separators=(',', ':'))

def pqc_like_hash(data_str: str) -> str:
    # simple deterministic post-quantum-like hash (SHA-256 here for demo)
    # If you have quantum_security.pqc_hash_key, call that instead.
    return hashlib.sha256(data_str.encode()).hexdigest()

app = Flask(__name__, template_folder="templates", static_folder="static")


# Single-node demo (for seminar). For multi-node you can run multiple copies and use register/sync endpoints.
blockchain = Blockchain()
@app.route('/fetch_weather', methods=['POST'])
def fetch_weather_and_add_block():
    """
    Expects JSON: {"lat": <float>, "lon": <float>, "use_mine": true/false}
    Steps:
      1) fetch weather JSON from Open-Meteo
      2) form canonical payload
      3) compute pqc_hash
      4) sign hash using server's node key (or require client private key)
      5) add to blockchain (either pending -> mine or direct block add for demo)
    """
    req = request.get_json() or {}
    lat = req.get('lat', 28.6139)   # default: New Delhi
    lon = req.get('lon', 77.2090)
    use_mine = req.get('use_mine', True)

    # 1) Fetch live data (Open-Meteo)
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        return jsonify({"success": False, "error": "API fetch failed", "status_code": r.status_code}), 502
    api_payload = r.json()

    # 2) canonicalize
    payload_str = canonical_json_str({"lat": lat, "lon": lon, "api": api_payload})

    # 3) compute PQC-like hash
    pqc_hash = pqc_like_hash(payload_str)

    # 4) sign (server-side) - use NodeAuth or cryptography directly
    # best: sign the pqc_hash with node's ECC private key (for demo we assume auth has sign method)
    signature_b64 = None
    try:
        # if you have NodeAuth() and it exposes sign_from_pem(private_pem, message)
        # auth = NodeAuth()
        # signature_b64 = auth.sign_hash_with_server_key(pqc_hash)
        # fallback: use a simple ECC signing using cryptography
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
        # Load server private key file if you saved one; else reuse previously generated private key in memory.
        # For demo let's assume you have a file 'server_private.pem' in project (or use a generated NodeAuth.private_key variable)
        try:
            with open("server_private.pem", "rb") as f:
                priv = serialization.load_pem_private_key(f.read(), password=None)
        except FileNotFoundError:
            # if not present, use NodeAuth to generate ephemeral key (not persistent) - replace with your own logic
            priv = auth.get_private_key_object()  # adapt to your ecc_auth API
        sig = priv.sign(pqc_hash.encode(), ec.ECDSA(hashes.SHA256()))
        import base64
        signature_b64 = base64.b64encode(sig).decode()
    except Exception as e:
        signature_b64 = None

    # 5) create block payload and add to blockchain
    block_data = {
        "api_source": "open-meteo",
        "lat": lat,
        "lon": lon,
        "payload": api_payload,
        "pqc_hash": pqc_hash,
        "ecc_signature": signature_b64,
        "timestamp": datetime.utcnow().isoformat()
    }

    # Option A: add as pending transaction and mine
    if use_mine and hasattr(blockchain, "add_transaction"):
        blockchain.add_transaction({"type": "api_data", "data": block_data})
        # you can auto-mine immediately for demo:
        mined_block = blockchain.mine()  # if your API returns mined block info
        return jsonify({"success": True, "message": "API data added and mined", "block": mined_block})

    # Option B: direct append block (if your class supports it)
    # fallback: create and append using blockchain API you have
    try:
        new_block = blockchain.add_api_block(block_data)  # implement this method if not present
        return jsonify({"success": True, "message": "API data added as block", "block": new_block})
    except Exception:
        # fallback return the data we would store
        return jsonify({"success": True, "message": "API data processed (not mined)", "data": block_data})
        @app.route('/verify_api_block', methods=['POST'])
def verify_api_block():
    """
    Expects JSON: {"block_index": <int>}
    Re-fetches the API for the lat/lon in that block, recomputes hash, compares stored pqc_hash.
    """
    req = request.get_json() or {}
    idx = req.get('block_index')
    if idx is None:
        return jsonify({"success": False, "error": "block_index required"}), 400

    try:
        block = blockchain.chain[idx]  # adjust to your structure
    except Exception:
        return jsonify({"success": False, "error": "block not found"}), 404

    lat = block.get('lat') or block.get('data', {}).get('lat')
    lon = block.get('lon') or block.get('data', {}).get('lon')
    # fetch current
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        return jsonify({"success": False, "error": "API fetch failed", "status_code": r.status_code}), 502
    current_payload = r.json()
    payload_str = canonical_json_str({"lat": lat, "lon": lon, "api": current_payload})
    current_hash = pqc_like_hash(payload_str)

    ok = (current_hash == block.get('pqc_hash'))
    return jsonify({"success": True, "match": ok, "stored_hash": block.get('pqc_hash'), "current_hash": current_hash})


auth = NodeAuth()

# ----------------- Helper: check signature of a transaction -----------------
def verify_transaction_signature(tx: dict) -> (bool, str):
    # tx must contain 'sender_public_key' (PEM string), 'signature' (base64), and the payload fields (recipient, amount)
    required = ['sender_public_key', 'signature', 'recipient', 'amount']
    for r in required:
        if r not in tx:
            return False, f"Missing field: {r}"
    try:
        sender_pub_pem = tx['sender_public_key'].encode('utf-8')
        signature = base64.b64decode(tx['signature'])
        # Build deterministic message bytes (string of sender->recipient:amount)
        message = json.dumps({
            "sender_public_key": tx['sender_public_key'],
            "recipient": tx['recipient'],
            "amount": tx['amount']
        }, sort_keys=True).encode('utf-8')

        pub_key = auth.deserialize_public_key(sender_pub_pem)
        valid = auth.verify_signature(pub_key, message, signature)
        return valid, "Signature valid" if valid else "Signature invalid"
    except Exception as e:
        return False, f"Exception during verify: {e}"

# ----------------- API endpoints -----------------

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/generate_keys', methods=['GET'])
def generate_keys():
    private_key, public_key = auth.generate_key_pair()
    priv_pem = auth.serialize_private_key(private_key).decode('utf-8')
    pub_pem = auth.serialize_public_key(public_key).decode('utf-8')
    # NOTE: For demo only — do not expose private keys in real systems
    return jsonify({
        "private_key_pem": priv_pem,
        "public_key_pem": pub_pem
    })

@app.route('/sign', methods=['POST'])
def sign():
    data = request.json
    if not data or 'private_key_pem' not in data or 'recipient' not in data or 'amount' not in data:
        return jsonify({"error": "private_key_pem, recipient, amount required"}), 400
    try:
        private_pem = data['private_key_pem'].encode('utf-8')
        private_key = auth.deserialize_private_key(private_pem)
        message = json.dumps({
            "sender_public_key": data.get('public_key_pem', ''),  # optional, but helpful
            "recipient": data['recipient'],
            "amount": data['amount']
        }, sort_keys=True).encode('utf-8')
        signature = auth.sign_message(private_key, message)
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        return jsonify({"signature": signature_b64})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/new_transaction', methods=['POST'])
def new_transaction():
    tx = request.json
    valid, msg = verify_transaction_signature(tx)
    if not valid:
        return jsonify({"success": False, "message": f"Invalid transaction: {msg}"}), 400
    # Add transaction to pending list
    blockchain.add_transaction({
        "sender_public_key": tx['sender_public_key'],
        "recipient": tx['recipient'],
        "amount": tx['amount'],
        "signature": tx['signature']
    })
    return jsonify({"success": True, "message": "Transaction added to pending pool"}), 201

@app.route('/mine', methods=['GET'])
def mine_block():
    # For simplicity, we mine whatever pending transactions exist
    idx = blockchain.mine()
    if not idx:
        return jsonify({"success": False, "message": "No transactions to mine"}), 400
    return jsonify({"success": True, "message": f"Block {idx} mined", "block_index": idx}), 200

@app.route('/get_chain', methods=['GET'])
def get_chain():
    chain_data = []
    for block in blockchain.chain:
        chain_data.append({
            "index": block.index,
            "timestamp": block.timestamp,
            "transactions": block.transactions,
            "previous_hash": block.previous_hash,
            "security_key": block.security_key,
            "nonce": block.nonce,
            "hash": block.hash
        })
    return jsonify({"length": len(chain_data), "chain": chain_data})

@app.route('/validate_chain', methods=['GET'])
def validate_chain():
    valid, msg = blockchain.is_chain_valid()
    return jsonify({"valid": valid, "message": msg})

# ----------------- Simple node-registering endpoints for multi-node demo -----------------
# NOTE: minimal implementations for seminar; for real-world you'd implement full consensus, http sync, etc.
nodes = set()

@app.route('/register_node', methods=['POST'])
def register_node():
    data = request.json
    if not data or 'node_url' not in data: 
        return jsonify({"error": "node_url required"}), 400
    nodes.add(data['node_url'])
    return jsonify({"message": "Node registered", "all_nodes": list(nodes)}), 201

@app.route('/nodes', methods=['GET'])
def list_nodes():
    return jsonify({"nodes": list(nodes)})

# ----------------- Run -----------------
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
