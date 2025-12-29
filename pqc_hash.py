import hashlib

def pqc_hash_key(qkd_key: str) -> str:
    """
    Generates a PQC-style secure hash using SHA-256.
    Input: QKD key (string)
    Output: Hexadecimal hash (string)
    """
    return hashlib.sha256(qkd_key.encode()).hexdigest()


def main():
    print("=== PQC Key Generator ===")

    # Example QKD key (in real system this comes from BB84)
    qkd_key = input("Enter QKD key: ")

    pqc_key = pqc_hash_key(qkd_key)

    print("\n✔ Original QKD Key:", qkd_key)
    print("✔ Generated PQC (SHA-256) Key:", pqc_key)

    print("\n--- Program Finished Successfully ---")


if __name__ == "__main__":
    main()
