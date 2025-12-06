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
        # Create a copy of the attributes, exclude 'hash' itself for consistent calculation
        block_data = self.__dict__.copy()
        block_data['hash'] = None 
        block_string = json.dumps(block_data, sort_keys=True) 
        return hashlib.sha256(block_string.encode()).hexdigest()

# --- Utility Function ---

def get_timestamp():
    return datetime.datetime.now()

# --- Blockchain Class Definition (Updated) ---

class Blockchain:
    # Set the mining difficulty: number of leading zeros required
    DIFFICULTY = 4 

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

    @staticmethod
    def proof_of_work(block, difficulty=DIFFICULTY):
        target = '0' * difficulty
        while block.hash[:difficulty] != target:
            block.nonce += 1
            block.hash = block.calculate_hash()
        return block.hash

    def mine(self):
        if not self.unconfirmed_transactions:
            return False

        last_block = self.last_block
        
        # 1. Create a new candidate block
        new_block = Block(
            index=last_block.index + 1,
            timestamp=get_timestamp(),
            transactions=self.unconfirmed_transactions,
            previous_hash=last_block.hash
        )

        # 2. Solve the Proof of Work
        proof = self.proof_of_work(new_block)

        # 3. If solved, reset transactions and add the new block
        self.unconfirmed_transactions = []
        self.chain.append(new_block)
        
        return new_block.index

# --- Test Mining (Verification) ---

if __name__ == '__main__':
    my_blockchain = Blockchain()
    
    # 1. Add transactions for Block 1
    my_blockchain.add_transaction({"sender": "A", "recipient": "B", "amount": 5})
    my_blockchain.add_transaction({"sender": "C", "recipient": "D", "amount": 12})
    
    # 2. Mine Block 1
    print("Starting mining Block 1...")
    mined_index = my_blockchain.mine()
    
    if mined_index:
        print(f"Block {mined_index} successfully mined and added.")
        print(f"Block 1 Hash (must start with {Blockchain.DIFFICULTY} zeros): {my_blockchain.last_block.hash}")
    
    # 3. Add transactions for Block 2
    my_blockchain.add_transaction({"sender": "E", "recipient": "F", "amount": 8})
    
    # 4. Mine Block 2
    print("\nStarting mining Block 2...")
    mined_index = my_blockchain.mine()
    
    if mined_index:
        print(f"Block {mined_index} successfully mined and added.")
        print(f"Block 2 Previous Hash (must match Block 1 Hash): {my_blockchain.last_block.previous_hash}")
        print(f"Block 2 Hash: {my_blockchain.last_block.hash}")