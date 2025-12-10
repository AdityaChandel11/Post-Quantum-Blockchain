# blockchain.py — replace your current file with this
import hashlib
import json
from time import time
from typing import List, Dict, Any, Optional

def canonical_json_str(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(',', ':'))

class Block:
    def __init__(self, index: int, timestamp: float, transactions: List[Dict], previous_hash: str, nonce: int = 0):
        self.index = index
        self.timestamp = timestamp
        # Important: store a deep-copied list/dict snapshot (no further mutation)
        # but we'll rely on the caller to pass immutable objects (we assume JSON-serializable)
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.compute_hash()

    def compute_hash(self) -> str:
        # Compute hash over a deterministic canonical JSON snapshot of block header + transactions
        block_header = {
            "index": self.index,
            "timestamp": round(float(self.timestamp), 6),   # rounding to avoid float tiny differences
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }
        block_string = canonical_json_str(block_header)
        return hashlib.sha256(block_string.encode('utf-8')).hexdigest()

    def to_dict(self) -> Dict:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash
        }

class Blockchain:
    def __init__(self):
        self.chain: List[Block] = []
        self.pending_transactions: List[Dict] = []
        # create genesis block
        self.create_genesis_block()

    def create_genesis_block(self):
        genesis = Block(index=0, timestamp=time(), transactions=[], previous_hash="0", nonce=0)
        self.chain.append(genesis)

    def add_transaction(self, transaction: Dict) -> int:
        """
        Add a transaction dict to the pending pool.
        Do NOT mutate the transaction after adding (caller should pass a snapshot).
        Returns the new length of pending pool for convenience.
        """
        # Make a deterministic snapshot copy of transaction to avoid later mutation issues
        # Only allow JSON-serializable values
        tx_snapshot = json.loads(canonical_json_str(transaction))
        self.pending_transactions.append(tx_snapshot)
        return len(self.pending_transactions)

    def last_block(self) -> Block:
        return self.chain[-1]

    def proof_of_work(self, block: Block, difficulty: int = 2) -> int:
        """
        Simple PoW: find nonce so that block.hash starts with '0' * difficulty.
        This is for demo only; you can set difficulty=0 to skip.
        """
        block.nonce = 0
        computed_hash = block.compute_hash()
        target = '0' * difficulty
        while not computed_hash.startswith(target):
            block.nonce += 1
            computed_hash = block.compute_hash()
        return block.nonce

    def mine(self) -> Optional[int]:
        """
        Create a new block with pending transactions.
        Returns the new block index on success or None if no transactions to mine.
        """
        if not self.pending_transactions:
            return None

        last = self.last_block()
        index = last.index + 1
        timestamp = time()
        # Use a snapshot of pending transactions and then clear the pending pool
        transactions_snapshot = json.loads(canonical_json_str(self.pending_transactions))
        new_block = Block(index=index, timestamp=timestamp, transactions=transactions_snapshot, previous_hash=last.hash, nonce=0)

        # Optional: small PoW for demo; set difficulty to 0 if you want instant mining
        try:
            difficulty = 0  # set to 0 for seminar speed; change to 2 if you want slow pow
            if difficulty > 0:
                new_block.nonce = self.proof_of_work(new_block, difficulty=difficulty)
            new_block.hash = new_block.compute_hash()
        except Exception:
            new_block.hash = new_block.compute_hash()

        # append to chain and clear pending transactions
        self.chain.append(new_block)
        self.pending_transactions = []
        return new_block.index

    def is_chain_valid(self) -> (bool, str):
        """
        Validate the chain: every block's stored hash must equal recomputed hash and previous_hash must match.
        Returns (True, "OK") or (False, "Hash mismatch at block X").
        """
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            # Recompute hash from the block header fields (index, timestamp rounded, transactions, previous_hash, nonce)
            recomputed = current.compute_hash()
            if recomputed != current.hash:
                return False, f"Hash mismatch at block {current.index}"
            if current.previous_hash != previous.hash:
                return False, f"Previous hash mismatch at block {current.index}"
        return True, "OK"

    # convenience for debug: export chain as list of dicts
    def to_dict_chain(self):
        return [blk.to_dict() for blk in self.chain]

