import hashlib
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric import utils as ec_utils
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

class NodeAuth:
    def __init__(self):
        self.curve = ec.SECP256R1()
        self.key_backend = default_backend()
        print(f"NodeAuth initialized using {self.curve.name} curve.")

    def generate_key_pair(self) -> tuple[ec.EllipticCurvePrivateKey, ec.EllipticCurvePublicKey]:
        # Generate the private key
        private_key = ec.generate_private_key(
            self.curve,
            self.key_backend
        )
        public_key = private_key.public_key()
        
        return private_key, public_key

    @staticmethod
    def _hash_message(message: str) -> bytes:
        digest = hashes.Hash(hashes.SHA256(), default_backend())
        digest.update(message.encode('utf-8'))
        return digest.finalize()

    def sign_message(self, private_key: ec.EllipticCurvePrivateKey, message: str) -> bytes:
        message_hash = self._hash_message(message)
        
        signature = private_key.sign(
            message_hash,
            ec.ECDSA(hashes.SHA256())
        )
        return signature

    def verify_signature(self, public_key: ec.EllipticCurvePublicKey, message: str, signature: bytes) -> bool:
        message_hash = self._hash_message(message)
        
        try:
            public_key.verify(
                signature,
                message_hash,
                ec.ECDSA(hashes.SHA256())
            )
            return True
        except InvalidSignature:
            return False
        except Exception as e:
            print(f"Verification Error: {e}")
            return False
    # Utility methods for storing/loading keys (serialization)
    @staticmethod
    def serialize_private_key(private_key: ec.EllipticCurvePrivateKey, password: str) -> bytes:
        return private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(password.encode('utf-8'))
        )

    @staticmethod
    def deserialize_private_key(pem_data: bytes, password: str) -> ec.EllipticCurvePrivateKey:
        return serialization.load_pem_private_key(
            pem_data,
            password=password.encode('utf-8'),
            backend=default_backend()
        )

    @staticmethod
    def serialize_public_key(public_key: ec.EllipticCurvePublicKey) -> bytes:
        return public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

    @staticmethod
    def deserialize_public_key(pem_data: bytes) -> ec.EllipticCurvePublicKey:
        return serialization.load_pem_public_key(
            pem_data,
            backend=default_backend()
        )
# --- Example Usage ---
if __name__ == "__main__":
    
    auth_tool = NodeAuth()

    private_key, public_key = auth_tool.generate_key_pair()
    print("\n--- Key Generation Complete ---")

    transaction_message = '{"from": "NodeA", "to": "NodeB", "amount": 100, "fee": 0.001}'
    print(f"Message to Sign: {transaction_message}")

    signature_bytes = auth_tool.sign_message(private_key, transaction_message)
    print(f"\nSignature generated (Length {len(signature_bytes)} bytes): {signature_bytes.hex()[:40]}...")

    is_valid = auth_tool.verify_signature(public_key, transaction_message, signature_bytes)
    
    print(f"\nVerification Result (Correct Key/Message): {is_valid}")

    tampered_message = transaction_message.replace("100", "5000")
    is_invalid = auth_tool.verify_signature(public_key, tampered_message, signature_bytes)
    
    print(f"Verification Result (Tampered Message): {is_invalid}")

    print("\n--- Key Serialization Example ---")
    
    secure_password = "a-strong-password-for-private-key-file"
    
    public_pem = NodeAuth.serialize_public_key(public_key)
    print(f"Serialized Public Key (for sharing):\n{public_pem.decode()[:15]}...\n")

    private_pem = NodeAuth.serialize_private_key(private_key, secure_password)
    print(f"Serialized Private Key (ENCRYPTED):\n{private_pem.decode()[:15]}...\n")
    
    loaded_private_key = NodeAuth.deserialize_private_key(private_pem, secure_password)
    
    test_signature = auth_tool.sign_message(loaded_private_key, "Test Load")
    is_loaded_valid = auth_tool.verify_signature(public_key, "Test Load", test_signature)
    print(f"Verification after load: {is_loaded_valid}")
