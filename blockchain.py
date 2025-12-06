import hashlib
import datetime
import json
import hashlib
import datetime
import json

class Block:
    def __init__(self, index, timestamp, transactions, previous_hash, nonce=0):
        self.index = index
        # Store timestamp as a string to make it JSON serializable
        self.timestamp = timestamp.isoformat() if isinstance(timestamp, datetime.datetime) else timestamp
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash() 

    def calculate_hash(self):
        # We need to serialize the block's data before hashing.
        block_string = json.dumps(self.__dict__, sort_keys=True) 
        return hashlib.sha256(block_string.encode()).hexdigest()

# --- Utility Function ---

def get_timestamp():
    return datetime.datetime.now()

# --- Blockchain Class Definition ---

class Blockchain:
    def __init__(self):
        self.chain = []
        self.unconfirmed_transactions = []
        self.create_genesis_block()

    def create_genesis_block(self):
        """Creates the first block (index 0)."""
        genesis_block = Block(
            index=0,
            timestamp=get_timestamp(),
            transactions=["The very first block is created."],
            previous_hash="0" * 64,
            nonce=0
        )
        self.chain.append(genesis_block)

    @property
    def last_block(self):
        """Returns the most recently added block."""
        return self.chain[-1]

    def add_transaction(self, transaction):
        """Adds a new transaction to the list of pending transactions."""
        self.unconfirmed_transactions.append(transaction)

# --- Verification Test ---

if __name__ == '__main__':
    my_blockchain = Blockchain()
    print("--- Step 2 Verification ---")
    print(f"Chain length: {len(my_blockchain.chain)}")
    print(f"Genesis Block Hash: {my_blockchain.last_block.hash}")
    my_blockchain.add_transaction({"sender": "X", "recipient": "Y", "amount": 100})
    print(f"Pending Transactions: {my_blockchain.unconfirmed_transactions}")