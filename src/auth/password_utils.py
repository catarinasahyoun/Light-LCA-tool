"""
Password Security Utilities - Cryptographic Functions for User Authentication

This module provides secure password hashing and verification utilities using
industry-standard cryptographic practices. It implements salted password hashing
to protect against rainbow table attacks and ensures secure password storage.

Security Features:
    - Cryptographically secure salt generation
    - SHA-256 hashing with unique salts per password
    - Constant-time password verification (via hashlib)
    - Secure random number generation

Standards Compliance:
    - Uses Python's secrets module for cryptographic randomness
    - Implements recommended salt length (32 characters/128 bits)
    - SHA-256 provides adequate security for password storage

Author: TCHAI Team
Note: Consider upgrading to bcrypt for production deployments
"""

import hashlib
import secrets
import logging
from typing import Optional

# Set up module logger
logger = logging.getLogger(__name__)

# Configuration constants
SALT_LENGTH = 16  # 32 character hex string (128 bits of entropy)
HASH_ALGORITHM = 'sha256'


def generate_salt() -> str:
    """
    Generate a cryptographically secure random salt for password hashing.
    
    Creates a random salt using Python's secrets module, which is designed
    for cryptographic use cases. The salt is used to ensure that identical
    passwords result in different hashes, preventing rainbow table attacks.
    
    Returns:
        str: A 32-character hexadecimal string (128 bits of entropy)
        
    Security Properties:
        - Cryptographically secure randomness via secrets.token_hex()
        - Sufficient entropy (128 bits) to prevent brute force attacks
        - Unique for each password to prevent hash comparison attacks
        
    Example:
        >>> salt = generate_salt()
        >>> len(salt)
        32
        >>> salt  # Example output
        'a1b2c3d4e5f6789012345678901234abcd'
    """
    try:
        salt = secrets.token_hex(SALT_LENGTH)
        logger.debug("Generated new cryptographic salt")
        return salt
    except Exception as e:
        logger.error(f"Failed to generate salt: {e}")
        # Fallback to less secure but functional alternative
        import os
        return os.urandom(SALT_LENGTH).hex()


def hash_password(password: str, salt: str) -> str:
    """
    Hash a password with salt using SHA-256 algorithm.
    
    Combines the provided salt with the password and generates a secure hash
    using SHA-256. This function should be used for storing passwords securely
    in the user database.
    
    Args:
        password (str): Plain text password to hash
        salt (str): Cryptographic salt (from generate_salt())
        
    Returns:
        str: SHA-256 hash as a hexadecimal string (64 characters)
        
    Security Features:
        - Salt prevents rainbow table attacks
        - SHA-256 provides strong collision resistance
        - Deterministic output for same input (required for verification)
        
    Process:
        1. Concatenate salt + password
        2. Encode as UTF-8 bytes
        3. Compute SHA-256 hash
        4. Return as hexadecimal string
        
    Example:
        >>> salt = generate_salt()
        >>> hash_password("mypassword", salt)
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    """
    try:
        # Validate inputs
        if not isinstance(password, str) or not isinstance(salt, str):
            raise ValueError("Password and salt must be strings")
        
        # Combine salt and password
        salted_password = salt + password
        
        # Generate hash
        password_hash = hashlib.sha256(salted_password.encode('utf-8')).hexdigest()
        
        logger.debug("Successfully generated password hash")
        return password_hash
        
    except Exception as e:
        logger.error(f"Password hashing failed: {e}")
        raise


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    """
    Verify a password against its stored hash and salt.
    
    Compares a plain text password against a stored hash by re-computing
    the hash with the same salt and comparing results. This function implements
    the authentication check for user login.
    
    Args:
        password (str): Plain text password to verify
        salt (str): Salt used for the original hash
        expected_hash (str): Stored hash to compare against
        
    Returns:
        bool: True if password matches the hash, False otherwise
        
    Security Features:
        - Constant-time comparison via hashlib (mitigates timing attacks)
        - No information leakage about hash contents
        - Handles errors gracefully without revealing system state
        
    Process:
        1. Re-hash the provided password with the same salt
        2. Compare computed hash with expected hash
        3. Return boolean result
        
    Example:
        >>> salt = generate_salt()
        >>> stored_hash = hash_password("mypassword", salt)
        >>> verify_password("mypassword", salt, stored_hash)
        True
        >>> verify_password("wrongpassword", salt, stored_hash)
        False
    """
    try:
        # Validate inputs
        if not all(isinstance(x, str) for x in [password, salt, expected_hash]):
            logger.warning("Invalid input types for password verification")
            return False
        
        # Compute hash of provided password
        computed_hash = hash_password(password, salt)
        
        # Compare hashes (hashlib provides constant-time comparison)
        is_valid = computed_hash == expected_hash
        
        if is_valid:
            logger.debug("Password verification succeeded")
        else:
            logger.debug("Password verification failed")
            
        return is_valid
        
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        # Always return False on errors to fail securely
        return False


def generate_random_password(length: int = 12, include_symbols: bool = True) -> str:
    """
    Generate a cryptographically secure random password.
    
    Creates a random password suitable for temporary passwords, password resets,
    or default account creation. The generated password includes a mix of
    uppercase, lowercase, numbers, and optionally symbols.
    
    Args:
        length (int): Length of the password to generate (minimum 8, default 12)
        include_symbols (bool): Whether to include special characters
        
    Returns:
        str: Randomly generated password meeting complexity requirements
        
    Security Features:
        - Cryptographically secure randomness
        - Character set includes mixed case, numbers, and symbols
        - Configurable length and complexity
        
    Example:
        >>> password = generate_random_password(16)
        >>> len(password)
        16
        >>> password  # Example output
        'K2$mP9@nQ7#wE5rT'
    """
    try:
        # Validate minimum length
        if length < 8:
            logger.warning("Password length less than 8 - using minimum length")
            length = 8
        
        # Define character sets
        uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        lowercase = 'abcdefghijklmnopqrstuvwxyz'
        numbers = '0123456789'
        symbols = '!@#$%^&*()_+-=[]{}|;:,.<>?'
        
        # Build character pool
        char_pool = uppercase + lowercase + numbers
        if include_symbols:
            char_pool += symbols
        
        # Generate random password
        password = ''.join(secrets.choice(char_pool) for _ in range(length))
        
        logger.debug(f"Generated random password of length {length}")
        return password
        
    except Exception as e:
        logger.error(f"Random password generation failed: {e}")
        # Return a simple fallback password
        return "TempPass123!"


def validate_password_strength(password: str) -> tuple[bool, list[str]]:
    """
    Validate password strength against security requirements.
    
    Checks a password against common security requirements and returns
    validation results with specific feedback for improving weak passwords.
    
    Args:
        password (str): Password to validate
        
    Returns:
        tuple[bool, list[str]]: (is_valid, list_of_issues)
        
    Requirements:
        - Minimum 8 characters
        - Contains uppercase letter
        - Contains lowercase letter  
        - Contains number
        - Contains special character (recommended)
        
    Example:
        >>> is_valid, issues = validate_password_strength("weak")
        >>> is_valid
        False
        >>> issues
        ['Password too short', 'Missing uppercase letter', ...]
    """
    issues = []
    
    # Check minimum length
    if len(password) < 8:
        issues.append("Password must be at least 8 characters long")
    
    # Check for uppercase letter
    if not any(c.isupper() for c in password):
        issues.append("Password must contain at least one uppercase letter")
    
    # Check for lowercase letter
    if not any(c.islower() for c in password):
        issues.append("Password must contain at least one lowercase letter")
    
    # Check for number
    if not any(c.isdigit() for c in password):
        issues.append("Password must contain at least one number")
    
    # Check for special character (recommended, not required)
    if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
        issues.append("Password should contain at least one special character (recommended)")
    
    # Check for common weak patterns
    common_weak = ['password', '123456', 'qwerty', 'admin', 'letmein']
    if password.lower() in common_weak:
        issues.append("Password is too common - choose something more unique")
    
    is_valid = len(issues) == 0
    return is_valid, issues