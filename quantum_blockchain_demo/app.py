# app.py
from flask import Flask, request, jsonify, render_template
from blockchain import Blockchain
from ecc_auth import NodeAuth
import json
import base64

app = Flask(__name__, template_folder="templates", static_folder="static")


# Single-node demo (for seminar). For multi-node you can run multiple copies and use register/sync endpoints.
blockchain = Blockchain()
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
