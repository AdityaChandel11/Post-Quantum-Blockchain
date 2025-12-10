# blockchain.py
import hashlib
import datetime
import json
from quantum_security import generate_final_key

class Block:
    def __init__(self, index, timestamp, transactions, previous_hash, security_key, nonce=0):
        self.index = index
        self.timestamp = timestamp.isoformat() if isinstance(timestamp, datetime.datetime) else str(timestamp)
        self.transactions = transactions  # list of transaction dicts
        self.previous_hash = previous_hash
        self.security_key = security_key  # from quantum_security.generate_final_key()
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        # exclude the 'hash' itself to produce consistent result
        block_data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "security_key": self.security_key,
            "nonce": self.nonce
        }
        block_string = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

class Blockchain:
    DIFFICULTY = 4  # same as your code

    def __init__(self):
        self.chain = []
        self.unconfirmed_transactions = []
        self.create_genesis_block()

    def create_genesis_block(self):
        key = generate_final_key()
        genesis_block = Block(
            index=0,
            timestamp=datetime.datetime.now(),
            transactions=[{"note": "Genesis Block"}],
            previous_hash="0" * 64,
            security_key=key,
            nonce=0
        )
        self.chain.append(genesis_block)

    @property
    def last_block(self):
        return self.chain[-1]

    def add_transaction(self, transaction: dict):
        """Transaction must be a dict with keys:
           'sender_public_key' (PEM), 'recipient', 'amount', 'signature' (base64 of signature)
        """
        self.unconfirmed_transactions.append(transaction)

    @staticmethod
    def proof_of_work(block: Block, difficulty=DIFFICULTY):
        target = '0' * difficulty
        while True:
            block.hash = block.calculate_hash()
            if block.hash.startswith(target):
                return block.hash
            block.nonce += 1

    def mine(self):
        if not self.unconfirmed_transactions:
            return False

        last_block = self.last_block
        new_block = Block(
            index=last_block.index + 1,
            timestamp=datetime.datetime.now(),
            transactions=self.unconfirmed_transactions.copy(),
            previous_hash=last_block.hash,
            security_key=generate_final_key()
        )
        proof = self.proof_of_work(new_block, self.DIFFICULTY)

        # on success, clear pending and add block
        self.unconfirmed_transactions = []
        self.chain.append(new_block)
        return new_block.index

    def is_chain_valid(self):
        # Validate whole chain: links + hash + difficulty + security_key present
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            if current.previous_hash != previous.hash:
                return False, f"Broken link at block {i}"

            if current.hash != current.calculate_hash():
                return False, f"Hash mismatch at block {i}"

            if not current.hash.startswith('0' * self.DIFFICULTY):
                return False, f"Proof of work missing at block {i}"

            # security_key should be present (basic check)
            if not current.security_key or len(current.security_key) < 64:
                return False, f"Security key missing/invalid at block {i}"

        return True, "Chain valid"
