import random
import hashlib

def generate_qkd_key():
    bits = [str(random.randint(0,1)) for _ in range(128)]
    bit_string = ''.join(bits)
    key = hashlib.sha256(bit_string.encode()).hexdigest()
    return key

def encrypt_message(message, key):
    return hashlib.sha256((key + message).encode()).hexdigest()
