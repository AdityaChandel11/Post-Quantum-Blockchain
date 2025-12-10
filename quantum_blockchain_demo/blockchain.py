# blockchain.py — minimal robust blockchain (no Flask, no routes)
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
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.compute_hash()

    def compute_hash(self) -> str:
        block_header = {
            "index": self.index,
            "timestamp": round(float(self.timestamp), 6),
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
        self.create_genesis_block()

    def create_genesis_block(self):
        genesis = Block(index=0, timestamp=time(), transactions=[], previous_hash="0", nonce=0)
        self.chain.append(genesis)

    def add_transaction(self, transaction: Dict) -> int:
        # snapshot transaction to avoid mutation
        tx_snapshot = json.loads(canonical_json_str(transaction))
        self.pending_transactions.append(tx_snapshot)
        return len(self.pending_transactions)

    def last_block(self) -> Block:
        return self.chain[-1]

    def proof_of_work(self, block: Block, difficulty: int = 0) -> int:
        block.nonce = 0
        computed_hash = block.compute_hash()
        target = '0' * difficulty
        while difficulty > 0 and not computed_hash.startswith(target):
            block.nonce += 1
            computed_hash = block.compute_hash()
        return block.nonce

    def mine(self) -> Optional[int]:
        if not self.pending_transactions:
            return None
        last = self.last_block()
        index = last.index + 1
        timestamp = time()
        transactions_snapshot = json.loads(canonical_json_str(self.pending_transactions))
        new_block = Block(index=index, timestamp=timestamp, transactions=transactions_snapshot, previous_hash=last.hash, nonce=0)
        try:
            difficulty = 0
            if difficulty > 0:
                new_block.nonce = self.proof_of_work(new_block, difficulty=difficulty)
            new_block.hash = new_block.compute_hash()
        except Exception:
            new_block.hash = new_block.compute_hash()
        self.chain.append(new_block)
        self.pending_transactions = []
        return new_block.index

    def inspect_block_hash(self, block_index: int) -> dict:
        if block_index < 0 or block_index >= len(self.chain):
            return {"ok": False, "error": "block not found", "index": block_index}
        block = self.chain[block_index]
        stored_hash = getattr(block, "hash", None)
        try:
            recomputed = block.compute_hash()
        except Exception as e:
            return {"ok": False, "error": f"recompute error: {e}", "index": block_index}
        previous_hash_stored = getattr(block, "previous_hash", None)
        previous_hash_expected = getattr(self.chain[block_index-1], "hash", None) if block_index > 0 else None
        prev_ok = (previous_hash_stored == previous_hash_expected) if block_index > 0 else True
        return {
            "ok": (recomputed == stored_hash) and prev_ok,
            "index": block_index,
            "recomputed": recomputed,
            "stored": stored_hash,
            "previous_ok": prev_ok,
            "previous_hash_stored": previous_hash_stored,
            "previous_hash_expected": previous_hash_expected
        }

    def is_chain_valid(self) -> (bool, str, list):
        problems = []
        for i in range(1, len(self.chain)):
            report = self.inspect_block_hash(i)
            if not report.get("ok", False):
                problems.append(report)
        if problems:
            return False, f"{len(problems)} problem(s) found", problems
        return True, "OK", []

    def to_dict_chain(self):
        return [blk.to_dict() for blk in self.chain]
