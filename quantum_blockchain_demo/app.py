# app.py
from flask import Flask, request, jsonify, render_template
import json
import requests
import hashlib
from datetime import datetime, timezone

# local imports
from blockchain import Blockchain
# Note: ensure ecc_auth.py exists in your project; NodeAuth is used for sign/verify endpoints.
try:
    from ecc_auth import NodeAuth
    auth = NodeAuth()
except Exception:
    # provide a dummy fallback if ecc_auth not present (so app still runs)
    class _DummyAuth:
        def generate_key_pair(self): return (None, None)
        def serialize_private_key(self, k): return b''
        def serialize_public_key(self, k): return b''
        def deserialize_private_key(self, p): raise Exception("No ECC auth")
        def deserialize_public_key(self, p): raise Exception("No ECC auth")
        def sign_message(self, k, m): raise Exception("No ECC auth")
        def verify_signature(self, pk, msg, sig): return False
    auth = _DummyAuth()

# ---------------- utilities ----------------
def canonical_json_str(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'))

def pqc_like_hash(data_str: str) -> str:
    # demo PQC-like hash (SHA-256 for example)
    return hashlib.sha256(data_str.encode('utf-8')).hexdigest()

# ---------------- app + blockchain ----------------
app = Flask(__name__, template_folder="templates", static_folder="static")
blockchain = Blockchain()

# ---------------- fetch weather and add (stable hashing using current_weather) ----------------
@app.route('/fetch_weather', methods=['POST'])
def fetch_weather_and_add_block():
    req = request.get_json() or {}
    lat = req.get('lat')
    lon = req.get('lon')
    use_mine = req.get('use_mine', True)

    if lat is None or lon is None:
        return jsonify({"success": False, "error": "lat and lon required"}), 400
    try:
        lat = float(lat); lon = float(lon)
    except Exception:
        return jsonify({"success": False, "error": "lat and lon must be numeric"}), 400

    # fetch Open-Meteo current_weather
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return jsonify({"success": False, "error": "API fetch failed", "status_code": r.status_code}), 502
        api_json = r.json()
    except Exception as e:
        return jsonify({"success": False, "error": f"API fetch exception: {e}"}), 502

    # stable weather: use only current_weather field if available
    weather_stable = api_json.get("current_weather") if isinstance(api_json, dict) and "current_weather" in api_json else api_json

    # convert API UTC time to local display-only string (do NOT include this in hash)
    api_time_str = None
    local_time_str = None
    try:
        if isinstance(weather_stable, dict) and weather_stable.get("time"):
            api_time_str = weather_stable.get("time")
            dt = datetime.fromisoformat(api_time_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            local_time_str = dt.astimezone().isoformat(timespec='minutes')
    except Exception:
        local_time_str = None

    # canonical payload used for hashing (round lat/lon)
    payload_for_hash = {
        "lat": round(float(lat), 6),
        "lon": round(float(lon), 6),
        "weather": weather_stable
    }
    payload_str = canonical_json_str(payload_for_hash)
    pqc_hash = pqc_like_hash(payload_str)

    # transaction stored in block (include local_time for display only)
    tx = {
        "lat": payload_for_hash["lat"],
        "lon": payload_for_hash["lon"],
        "weather": weather_stable,
        "pqc_hash": pqc_hash,
        "stored_payload": payload_for_hash,   # debug-friendly
        "local_time": local_time_str,
        "timestamp": datetime.utcnow().isoformat()
    }

    try:
        blockchain.add_transaction(tx)
    except Exception as e:
        return jsonify({"success": False, "error": f"blockchain.add_transaction error: {e}"}), 500

    if use_mine:
        try:
            block_index = blockchain.mine()
        except Exception as e:
            return jsonify({"success": False, "error": f"blockchain.mine error: {e}"}), 500
    else:
        block_index = None

    return jsonify({"success": True, "message": "API data added and mined" if use_mine else "API data added (pending)", "block": block_index}), 200

# ---------------- verify API block (re-fetch current_weather and re-hash) ----------------
@app.route('/verify_api_block', methods=['POST'])
def verify_api_block():
    req = request.get_json() or {}
    idx = req.get("block_index")
    if idx is None:
        return jsonify({"success": False, "error": "block_index required"}), 400
    try:
        idx = int(idx)
    except Exception:
        return jsonify({"success": False, "error": "block_index must be integer"}), 400

    if idx < 0 or idx >= len(blockchain.chain):
        return jsonify({"success": False, "error": "block not found"}), 404

    block = blockchain.chain[idx]
    # extract tx candidates
    transactions = []
    if isinstance(block, dict):
        transactions = block.get("transactions") or block.get("payload") or []
        if block.get("pqc_hash") and (block.get("lat") is not None or block.get("weather") is not None):
            transactions = [block] + (transactions if isinstance(transactions, list) else [])
    else:
        transactions = getattr(block, "transactions", None) or getattr(block, "payload", None) or []
        if not isinstance(transactions, list):
            transactions = [transactions] if transactions else []
        maybe = {"lat": getattr(block, "lat", None), "lon": getattr(block, "lon", None), "pqc_hash": getattr(block, "security_key", None) or getattr(block, "pqc_hash", None)}
        if maybe.get("pqc_hash"):
            transactions.insert(0, maybe)

    if not isinstance(transactions, list):
        transactions = [transactions]

    found = None
    for tx in transactions:
        if not isinstance(tx, dict):
            continue
        if tx.get("pqc_hash") and (tx.get("lat") is not None or tx.get("weather") is not None):
            found = tx
            break

    if not found:
        return jsonify({"success": False, "error": "API transaction not found inside block"}), 400

    lat = found.get("lat"); lon = found.get("lon"); stored_hash = found.get("pqc_hash")
    if lat is None or lon is None or stored_hash is None:
        return jsonify({"success": False, "error": "lat/lon/pqc_hash missing in stored tx"}), 400

    # re-fetch current_weather
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return jsonify({"success": False, "error": "API fetch failed", "status_code": r.status_code}), 502
        api_json = r.json()
    except Exception as e:
        return jsonify({"success": False, "error": f"API fetch exception: {e}"}), 502

    current_weather = api_json.get("current_weather") if isinstance(api_json, dict) else api_json
    payload_for_hash = {"lat": round(float(lat), 6), "lon": round(float(lon), 6), "weather": current_weather}
    payload_str = canonical_json_str(payload_for_hash)
    current_hash = pqc_like_hash(payload_str)

    match = (stored_hash == current_hash)
    return jsonify({"success": True, "match": match, "stored_hash": stored_hash, "current_hash": current_hash}), 200

# ---------------- inspect block & tamper endpoints (demo) ----------------
@app.route('/inspect_block', methods=['GET'])
def inspect_block():
    idx = request.args.get('index')
    if idx is None:
        return jsonify({"success": False, "error": "index query param required"}), 400
    try:
        idx = int(idx)
    except Exception:
        return jsonify({"success": False, "error": "index must be integer"}), 400

    valid, msg, details = blockchain.is_chain_valid()
    try:
        report = blockchain.inspect_block_hash(idx)
    except Exception as e:
        return jsonify({"success": False, "error": f"inspect error: {e}"}), 500

    return jsonify({"success": True, "inspect": report, "chain_valid": valid, "message": msg, "problems": details}), 200

@app.route('/tamper_block', methods=['POST'])
def tamper_block():
    req = request.get_json() or {}
    needed = ['block_index', 'tx_index', 'field', 'new_value']
    if not all(k in req for k in needed):
        return jsonify({"success": False, "error": "block_index, tx_index, field, new_value required"}), 400
    bi = int(req['block_index']); ti = int(req['tx_index'])
    field = req['field']; new_value = req['new_value']

    if bi < 0 or bi >= len(blockchain.chain):
        return jsonify({"success": False, "error": "block not found"}), 404

    block = blockchain.chain[bi]
    txs = None
    if isinstance(block, dict):
        txs = block.get("transactions") or block.get("payload") or []
    else:
        txs = getattr(block, "transactions", None) or getattr(block, "payload", None) or []

    if not isinstance(txs, list) or ti < 0 or ti >= len(txs):
        return jsonify({"success": False, "error": "transaction index out of range"}), 400

    before = json.loads(json.dumps(txs[ti]))
    try:
        txs[ti][field] = new_value
    except Exception:
        try:
            txs[ti] = dict(txs[ti])
            txs[ti][field] = new_value
        except Exception as e:
            return jsonify({"success": False, "error": f"cannot mutate tx: {e}"}), 500

    after = json.loads(json.dumps(txs[ti]))
    report = blockchain.inspect_block_hash(bi)
    return jsonify({"success": True, "before": before, "after": after, "inspect": report}), 200

# ---------------- basic blockchain endpoints ----------------
@app.route('/mine', methods=['GET'])
def mine_block():
    idx = blockchain.mine()
    if idx is None:
        return jsonify({"success": False, "message": "No transactions to mine"}), 400
    return jsonify({"success": True, "message": f"Block {idx} mined", "block_index": idx}), 200

@app.route('/get_chain', methods=['GET'])
def get_chain():
    try:
        chain_data = blockchain.to_dict_chain()
    except Exception:
        # fallback: try to build a safe representation
        chain_data = []
        for blk in blockchain.chain:
            try:
                chain_data.append(blk.to_dict())
            except Exception:
                chain_data.append(blk if isinstance(blk, dict) else {})
    return jsonify({"length": len(chain_data), "chain": chain_data})

@app.route('/validate_chain', methods=['GET'])
def validate_chain():
    valid, msg, details = blockchain.is_chain_valid()
    return jsonify({"valid": valid, "message": msg, "problems": details})

@app.route('/pending', methods=['GET'])
def get_pending():
    return jsonify({"pending_count": len(blockchain.pending_transactions), "pending": blockchain.pending_transactions})

# ---------------- keys, sign, transaction endpoints (demo) ----------------
@app.route('/generate_keys', methods=['GET'])
def generate_keys():
    private_key, public_key = auth.generate_key_pair() if hasattr(auth, "generate_key_pair") else (None, None)
    priv_pem = auth.serialize_private_key(private_key).decode('utf-8') if private_key else ""
    pub_pem = auth.serialize_public_key(public_key).decode('utf-8') if public_key else ""
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
        signature_b64 = __import__('base64').b64encode(signature).decode('utf-8')
        return jsonify({"signature": signature_b64})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/new_transaction', methods=['POST'])
def new_transaction():
    tx = request.json
    # signature verification optional — we expect signed txs for demo
    blockchain.add_transaction(tx)
    return jsonify({"success": True, "message": "Transaction added to pending pool"}), 201

@app.route('/')
def index():
    return render_template("index.html")

# ---------------- run ----------------
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
