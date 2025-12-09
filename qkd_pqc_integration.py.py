import random
import hashlib
import datetime
import json

# ---------------- QKD SIMULATION (BB84) ---------------- #

def generate_bits(length=128):
    return ''.join(random.choice('01') for _ in range(length))

def generate_bases(length=128):
    return ''.join(random.choice(['+', 'x']) for _ in range(length))

def simulate_qkd():
    alice_bits = generate_bits()
    alice_bases = generate_bases()
    bob_bases = generate_bases()

    # Key generation by comparing bases
    key = ""
    for i in range(len(alice_bits)):
        if alice_bases[i] == bob_bases[i]:
            key += alice_bits[i]

    return key

# ---------------- PQC-LIKE HASH-BASED KEY ---------------- #

def pqc_hash_key(qkd_key):
    return hashlib.sha256(qkd_key.encode()).hexdigest()

# ---------------- Merge QKD + PQC Key ---------------- #

def generate_final_key():
    qkd_key = simulate_qkd()
    pqc_key = pqc_hash_key(qkd_key)
    final_key = hashlib.sha512((qkd_key + pqc_key).encode()).hexdigest()
    return final_key

# ---------------- Blockchain Block Class ---------------- #

class Block:
    def __init__(self, index, timestamp, transactions, previous_hash, security_key):
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.security_key = security_key
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = json.dumps({
            "index": self.index,
            "timestamp": str(self.timestamp),
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "security_key": self.security_key
        }, sort_keys=True).encode()

        return hashlib.sha256(block_string).hexdigest()

# ---------------- Blockchain Class ---------------- #

class Blockchain:
    def __init__(self):
        self.chain = []
        self.create_genesis_block()

    def create_genesis_block(self):
        key = generate_final_key()
        genesis_block = Block(
            index=0,
            timestamp=datetime.datetime.now(),
            transactions="Genesis Block",
            previous_hash="0"*64,
            security_key=key
        )
        self.chain.append(genesis_block)

    def add_block(self, transactions):
        prev_block = self.chain[-1]
        key = generate_final_key()

        block = Block(
            index=len(self.chain),
            timestamp=datetime.datetime.now(),
            transactions=transactions,
            previous_hash=prev_block.hash,
            security_key=key
        )
        self.chain.append(block)

# ---------------- Run Test ---------------- #

if __name__ == "__main__":
    blockchain = Blockchain()

    blockchain.add_block("Sender: Alice -> Bob : 50 coins")
    blockchain.add_block("Sender: Bob -> Charlie : 30 coins")

    print("\n✅ Blockchain with QKD + PQC Security\n")
    for block in blockchain.chain:
        print("Index:", block.index)
        print("Timestamp:", block.timestamp)
        print("Transactions:", block.transactions)
        print("Prev Hash:", block.previous_hash)
        print("Security Key:", block.security_key[:40], "...")  # short view
        print("Hash:", block.hash)
        print("-"*60)
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes

# Example: Block 1 ka security_key
block_key = blockchain.chain[1].security_key.encode()

# ECC key pair generate
private_key = ec.generate_private_key(ec.SECP256R1())
public_key = private_key.public_key()

# Sign the block key
signature = private_key.sign(block_key, ec.ECDSA(hashes.SHA256()))
print("Block 1 Signature:", signature)

# Verify the signature
try:
    public_key.verify(signature, block_key, ec.ECDSA(hashes.SHA256()))
    print("✅ Block 1 signature is valid")
except:
    print("❌ Block 1 signature is invalid")
for i in range(len(blockchain.chain)):
    block_key = blockchain.chain[i].security_key.encode()
    signature = private_key.sign(block_key, ec.ECDSA(hashes.SHA256()))
    print(f"Block {i} Signature:", signature)
    try:
        public_key.verify(signature, block_key, ec.ECDSA(hashes.SHA256()))
        print(f"✅ Block {i} signature is valid")
    except:
        print(f"❌ Block {i} signature is invalid")
