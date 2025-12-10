# ecc_auth.py
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend

class NodeAuth:
    def __init__(self):
        self.curve = ec.SECP256R1()
        self.backend = default_backend()

    def generate_key_pair(self):
        private_key = ec.generate_private_key(self.curve, self.backend)
        public_key = private_key.public_key()
        return private_key, public_key

    @staticmethod
    def serialize_private_key(private_key) -> bytes:
        return private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

    @staticmethod
    def serialize_public_key(public_key) -> bytes:
        return public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

    @staticmethod
    def deserialize_private_key(pem_data: bytes):
        return serialization.load_pem_private_key(pem_data, password=None, backend=default_backend())

    @staticmethod
    def deserialize_public_key(pem_data: bytes):
        return serialization.load_pem_public_key(pem_data, backend=default_backend())

    @staticmethod
    def _hash_message_bytes(message_bytes: bytes) -> bytes:
        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(message_bytes)
        return digest.finalize()

    def sign_message(self, private_key, message_bytes: bytes) -> bytes:
        # message_bytes should be deterministic JSON bytes (utf-8)
        message_hash = self._hash_message_bytes(message_bytes)
        signature = private_key.sign(message_hash, ec.ECDSA(hashes.SHA256()))
        return signature

    def verify_signature(self, public_key, message_bytes: bytes, signature: bytes) -> bool:
        message_hash = self._hash_message_bytes(message_bytes)
        try:
            public_key.verify(signature, message_hash, ec.ECDSA(hashes.SHA256()))
            return True
        except InvalidSignature:
            return False
        except Exception:
            return False

    # Extra helpers for base64 encoding of signatures
    @staticmethod
    def signature_to_b64(sig: bytes) -> str:
        return base64.b64encode(sig).decode('utf-8')

    @staticmethod
    def signature_from_b64(b64: str) -> bytes:
        return base64.b64decode(b64.encode('utf-8'))
