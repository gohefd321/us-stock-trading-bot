"""
API Key Encryption Service
Provides encryption/decryption for sensitive API keys using Fernet symmetric encryption
"""

from cryptography.fernet import Fernet
import os
from pathlib import Path


# Get project root directory (3 levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


class EncryptionService:
    """Service for encrypting and decrypting API keys"""

    def __init__(self, key_file: str = None):
        """
        Initialize encryption service

        Args:
            key_file: Path to encryption key file (defaults to PROJECT_ROOT/data/encryption.key)
        """
        if key_file is None:
            key_file = str(PROJECT_ROOT / "data" / "encryption.key")
        self.key_file = key_file
        self.key = self._load_or_generate_key()
        self.cipher = Fernet(self.key)

    def _load_or_generate_key(self) -> bytes:
        """Load existing encryption key or generate new one"""
        key_path = Path(self.key_file)

        # Create parent directory if it doesn't exist
        key_path.parent.mkdir(parents=True, exist_ok=True)

        if key_path.exists():
            # Load existing key
            with open(key_path, "rb") as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(key_path, "wb") as f:
                f.write(key)

            # Set restrictive permissions (owner read/write only)
            os.chmod(key_path, 0o600)

            print(f"Generated new encryption key at {key_path}")
            return key

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string

        Args:
            plaintext: Text to encrypt

        Returns:
            Encrypted text as base64 string
        """
        if not plaintext:
            raise ValueError("Cannot encrypt empty string")

        encrypted_bytes = self.cipher.encrypt(plaintext.encode('utf-8'))
        return encrypted_bytes.decode('utf-8')

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext string

        Args:
            ciphertext: Encrypted text to decrypt

        Returns:
            Decrypted plaintext string
        """
        if not ciphertext:
            raise ValueError("Cannot decrypt empty string")

        try:
            decrypted_bytes = self.cipher.decrypt(ciphertext.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")

    def rotate_key(self, new_key_file: str = None) -> None:
        """
        Rotate encryption key (advanced usage)

        Args:
            new_key_file: Path to new key file
        """
        # This would require re-encrypting all existing data
        # Left as placeholder for future implementation
        raise NotImplementedError("Key rotation not yet implemented")


# Global instance
_encryption_service: EncryptionService = None


def get_encryption_service() -> EncryptionService:
    """Get or create global encryption service instance"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service
