"""
Encryption utilities for sensitive data like OAuth tokens.
Uses Fernet (symmetric encryption) from cryptography library.
AES-128 in CBC mode with HMAC authentication.
"""

import os
from cryptography.fernet import Fernet
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class EncryptionManager:
    """Manages encryption/decryption of sensitive data"""
    
    def __init__(self):
        """Initialize with encryption key from environment"""
        encryption_key = os.getenv("TOKEN_ENCRYPTION_KEY")
        
        if not encryption_key:
            raise ValueError(
                "TOKEN_ENCRYPTION_KEY environment variable not set. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        
        try:
            self.cipher = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        except Exception as e:
            raise ValueError(f"Invalid TOKEN_ENCRYPTION_KEY format: {e}")
    
    def encrypt(self, plaintext: str) -> bytes:
        """
        Encrypt plaintext to bytes
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Encrypted bytes (safe to store in database)
        """
        if not plaintext:
            return None
        
        try:
            return self.cipher.encrypt(plaintext.encode())
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, ciphertext: bytes) -> str:
        """
        Decrypt bytes to plaintext
        
        Args:
            ciphertext: Encrypted bytes from database
            
        Returns:
            Decrypted string
        """
        if not ciphertext:
            return None
        
        try:
            return self.cipher.decrypt(ciphertext).decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise


# Singleton instance
_encryption_manager: Optional[EncryptionManager] = None


def get_encryption_manager() -> EncryptionManager:
    """Get or create encryption manager singleton"""
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager


def encrypt_token(token: str) -> bytes:
    """Convenience function to encrypt a token"""
    return get_encryption_manager().encrypt(token)


def decrypt_token(encrypted_token: bytes) -> str:
    """Convenience function to decrypt a token"""
    return get_encryption_manager().decrypt(encrypted_token)
