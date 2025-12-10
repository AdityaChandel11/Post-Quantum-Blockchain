# quantum_security.py
import random
import hashlib

# ---------------- QKD SIMULATION (BB84-like) ---------------- #

def generate_bits(length=128):
    return ''.join(random.choice('01') for _ in range(length))

def generate_bases(length=128):
    return ''.join(random.choice(['+', 'x']) for _ in range(length))

def simulate_qkd(length=128):
    alice_bits = generate_bits(length)
    alice_bases = generate_bases(length)
    bob_bases = generate_bases(length)

    # Key generation by comparing bases
    key = ""
    for i in range(len(alice_bits)):
        if alice_bases[i] == bob_bases[i]:
            key += alice_bits[i]

    return key

# ---------------- PQC-LIKE HASH-BASED KEY ---------------- #

def pqc_hash_key(qkd_key):
    if not qkd_key:
        qkd_key = "0"
    return hashlib.sha256(qkd_key.encode()).hexdigest()

# ---------------- Merge QKD + PQC Key ---------------- #

def generate_final_key(length=128):
    qkd_key = simulate_qkd(length)
    pqc_key = pqc_hash_key(qkd_key)
    final_key = hashlib.sha512((qkd_key + pqc_key).encode()).hexdigest()
    return final_key
