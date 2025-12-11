import random
import hashlib
import datetime
import json

def generate_bits(length=128):
    return ''.join(random.choice('01') for _ in range(length))

def generate_bases(length=128):
    return ''.join(random.choice(['+', 'x']) for _ in range(length))

def simulate_qkd():
    alice_bits = generate_bits()
    alice_bases = generate_bases()
    bob_bases = generate_bases()

    key = ""
    for i in range(len(alice_bits)):
        if alice_bases[i] == bob_bases[i]:
            key += alice_bits[i]
    return key

class Block:
    def __init__(self, index, timestamp, data, prev_hash, qkd_key):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.prev_hash = prev_hash
        self.qkd_key = qkd_key
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = json.dumps({
            "index": self.index,
            "timestamp": str(self.timestamp),
            "data": self.data,
            "prev_hash": self.prev_hash,
            "qkd_key": self.qkd_key
        }, sort_keys=True).encode()

        return hashlib.sha256(block_string).hexdigest()

class Blockchain:
    def __init__(self):
        self.chain = []
        self.create_genesis()

    def create_genesis(self):
        qkd_key = simulate_qkd()
        genesis = Block(0, datetime.datetime.now(), "Genesis", "0"*64, qkd_key)
        self.chain.append(genesis)

    def add_block(self, data):
        prev = self.chain[-1]
        qkd_key = simulate_qkd()
        block = Block(
            len(self.chain),
            datetime.datetime.now(),
            data,
            prev.hash,
            qkd_key
        )
        self.chain.append(block)

blockchain = Blockchain()
blockchain.add_block("Alice -> Bob : 50 coins")
blockchain.add_block("Bob -> Charlie : 30 coins")

for block in blockchain.chain:
    print("Index:", block.index)
    print("QKD Key:", block.qkd_key[:40], "...")
    print("Hash:", block.hash)
    print("-"*50)
