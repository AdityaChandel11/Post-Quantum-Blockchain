# app.py — Final demo file (copy-paste replace entire file)
from flask import Flask, request, jsonify, render_template
import json
import base64
import requests
import hashlib
from datetime import datetime

# Project imports (adjust path/names if your files are located elsewhere)
from blockchain import Blockchain
from ecc_auth import NodeAuth

# ----------------- Utilities -----------------
def canonical_json_str(obj):
    """Return deterministic JSON string for hashing."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'))

def pqc_like_hash(data_str: str) -> str:
    """Demo PQC-like hash (SHA-256 here for example)."""
    return hashlib.sha256(data_str.encode('utf-8')).hexdigest()

# ----------------- App + globals -----------------
app = Flask(__name__, template_folder="templates", static_folder="static")
blockchain = Blockchain()
auth = NodeAuth()

# ----------------- Fetch weather and add block (stable hashing: current_weather) -----------------
@app.route('/fetch_weather', methods=['POST'])
def fetch_weather_and_add_block():
    """
    Expects JSON: {"lat": <float>, "lon": <float>}
    Workflow:
      1) require lat/lon (no silent defaults)
      2) fetch Open-Meteo current_weather
      3) canonicalize payload using only current_weather and rounded lat/lon
      4) compute pqc_hash and store tx {lat, lon, weather, pqc_hash, timestamp}
      5) add_transaction() then mine()
      6) return mined block index
    """
    req = request.get_json() or {}
    lat = req.get('lat')
    lon = req.get('lon')

    # require lat & lon explicitly (universal for any teacher-supplied coord)
    if lat is None or lon is None:
        return jsonify({"success": False, "error": "lat and lon required"}), 400

    # validate numeric lat/lon
    try:
        lat = float(lat)
        lon = float(lon)
    except Exception:
        return jsonify({"success": False, "error": "lat and lon must be numeric"}), 400

    # fetch API (Open-Meteo current weather)
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return jsonify({"success": False, "error": "API fetch failed", "status_code": r.status_code}), 502
        api_json = r.json()
    except Exception as e:
        return jsonify({"success": False, "error": f"API fetch exception: {e}"}), 502

    # Use only the stable 'current_weather' object for hashing and storage
    weather_stable = None
    if isinstance(api_json, dict) and "current_weather" in api_json:
        weather_stable = api_json["current_weather"]
    else:
        # fallback if API returns an unexpected shape — use whole json (best-effort)
        weather_stable = api_json

    # canonical payload shape (round lat/lon to avoid float formatting differences)
    payload_for_hash = {
        "lat": round(float(lat), 6),
        "lon": round(float(lon), 6),
        "weather": weather_stable
    }
    payload_str = canonical_json_str(payload_for_hash)
    pqc_hash = pqc_like_hash(payload_str)

    # prepare transaction stored in block
    tx = {
        "lat": payload_for_hash["lat"],
        "lon": payload_for_hash["lon"],
        "weather": weather_stable,
        "pqc_hash": pqc_hash,
        "stored_payload": payload_for_hash,   # optional: helpful for debugging/inspection
        "timestamp": datetime.utcnow().isoformat()
    }

    # add transaction and mine immediately (works with your existing blockchain implementation)
    try:
        blockchain.add_transaction(tx)
    except Exception as e:
        return jsonify({"success": False, "error": f"blockchain.add_transaction error: {e}"}), 500

    try:
        block_index = blockchain.mine()
    except Exception as e:
        return jsonify({"success": False, "error": f"blockchain.mine error: {e}"}), 500

    return jsonify({"success": True, "message": "API data added and mined", "block": block_index}), 200

# ----------------- Verify API block (re-fetch current_weather and re-hash same shape) -----------------
@app.route('/verify_api_block', methods=['POST'])
def verify_api_block():
    """
    Expects JSON: {"block_index": <int>}
    Re-fetches Open-Meteo current_weather for the lat/lon stored in that block's transaction,
    recomputes canonical pqc_hash (same shape) and compares with stored pqc_hash.
    """
    req = request.get_json() or {}
    idx = req.get("block_index")
    if idx is None:
        return jsonify({"success": False, "error": "block_index required"}), 400

    try:
        idx = int(idx)
    except Exception:
        return jsonify({"success": False, "error": "block_index must be an integer"}), 400

    if idx < 0 or idx >= len(blockchain.chain):
        return jsonify({"success": False, "error": "block not found"}), 404

    block = blockchain.chain[idx]

    # Extract candidate transactions (support dict-block or object-block shapes)
    transactions = []
    if isinstance(block, dict):
        # common shape: {"transactions": [...]} or block may directly be the tx dict
        transactions = block.get("transactions") or block.get("payload") or []
        if block.get("pqc_hash") and (block.get("lat") is not None or block.get("weather") is not None):
            transactions = [block] + (transactions if isinstance(transactions, list) else [])
    else:
        # block object: try attributes
        transactions = getattr(block, "transactions", None) or getattr(block, "payload", None) or []
        if not isinstance(transactions, list):
            transactions = [transactions] if transactions else []
        # also allow top-level block attributes as candidate
        maybe = {
            "lat": getattr(block, "lat", None),
            "lon": getattr(block, "lon", None),
            "pqc_hash": getattr(block, "security_key", None) or getattr(block, "pqc_hash", None)
        }
        if maybe.get("pqc_hash"):
            transactions.insert(0, maybe)

    if not isinstance(transactions, list):
        transactions = [transactions]

    # Find the transaction that looks like our API tx (pqc_hash + lat/lon or weather)
    found = None
    for tx in transactions:
        if not isinstance(tx, dict):
            continue
        if tx.get("pqc_hash") and (tx.get("lat") is not None or tx.get("weather") is not None):
            found = tx
            break

    if not found:
        return jsonify({"success": False, "error": "API transaction not found inside block"}), 400

    lat = found.get("lat")
    lon = found.get("lon")
    stored_hash = found.get("pqc_hash")

    if lat is None or lon is None or stored_hash is None:
        return jsonify({"success": False, "error": "lat/lon/pqc_hash missing in stored tx"}), 400

    # Re-fetch same stable API field (current_weather)
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return jsonify({"success": False, "error": "API fetch failed", "status_code": r.status_code}), 502
        api_json = r.json()
    except Exception as e:
        return jsonify({"success": False, "error": f"API fetch exception: {e}"}), 502

    current_weather = api_json.get("current_weather") if isinstance(api_json, dict) else api_json

    payload_for_hash = {
        "lat": round(float(lat), 6),
        "lon": round(float(lon), 6),
        "weather": current_weather
    }
    payload_str = canonical_json_str(payload_for_hash)
    current_hash = pqc_like_hash(payload_str)

    match = (stored_hash == current_hash)
    return jsonify({"success": True, "match": match, "stored_hash": stored_hash, "current_hash": current_hash}), 200

# ----------------- Helper: signature verification (keeps existing behavior) -----------------
def verify_transaction_signature(tx: dict) -> (bool, str):
    required = ['sender_public_key', 'signature', 'recipient', 'amount']
    for r in required:
        if r not in tx:
            return False, f"Missing field: {r}"
    try:
        sender_pub_pem = tx['sender_public_key'].encode('utf-8')
        signature = base64.b64decode(tx['signature'])
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

# ----------------- Remaining API endpoints (unchanged) -----------------
@app.route('/')
def index():
    return render_template("index.html")

@app.route('/generate_keys', methods=['GET'])
def generate_keys():
    private_key, public_key = auth.generate_key_pair()
    priv_pem = auth.serialize_private_key(private_key).decode('utf-8')
    pub_pem = auth.serialize_public_key(public_key).decode('utf-8')
    return jsonify({"private_key_pem": priv_pem, "public_key_pem": pub_pem})

@app.route('/sign', methods=['POST'])
def sign():
    data = request.json
    if not data or 'private_key_pem' not in data or 'recipient' not in data or 'amount' not in data:
        return jsonify({"error": "private_key_pem, recipient, amount required"}), 400
    try:
        private_pem = data['private_key_pem'].encode('utf-8')
        private_key = auth.deserialize_private_key(private_pem)
        message = json.dumps({
            "sender_public_key": data.get('public_key_pem', ''),
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
    blockchain.add_transaction({
        "sender_public_key": tx['sender_public_key'],
        "recipient": tx['recipient'],
        "amount": tx['amount'],
        "signature": tx['signature']
    })
    return jsonify({"success": True, "message": "Transaction added to pending pool"}), 201

@app.route('/mine', methods=['GET'])
def mine_block():
    idx = blockchain.mine()
    if idx is None:
        return jsonify({"success": False, "message": "No transactions to mine"}), 400
    return jsonify({"success": True, "message": f"Block {idx} mined", "block_index": idx}), 200

@app.route('/get_chain', methods=['GET'])
def get_chain():
    chain_data = []
    for block in blockchain.chain:
        try:
            chain_data.append({
                "index": getattr(block, "index", None),
                "timestamp": getattr(block, "timestamp", None),
                "transactions": getattr(block, "transactions", None),
                "previous_hash": getattr(block, "previous_hash", None),
                "security_key": getattr(block, "security_key", None),
                "nonce": getattr(block, "nonce", None),
                "hash": getattr(block, "hash", None)
            })
        except Exception:
            chain_data.append(block if isinstance(block, dict) else {})
    return jsonify({"length": len(chain_data), "chain": chain_data})

@app.route('/validate_chain', methods=['GET'])
def validate_chain():
    valid, msg = blockchain.is_chain_valid()
    return jsonify({"valid": valid, "message": msg})

# ----------------- Node endpoints -----------------
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
    # Keep debug=True during development / demo so you can see tracebacks in terminal
    app.run(host='0.0.0.0', port=5000, debug=True)
