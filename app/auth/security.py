from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import base64

load_dotenv()

# JWT Configuration with validation
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise ValueError(
        "JWT_SECRET_KEY must be set in .env and at least 32 characters. "
        "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(64))'"
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Encryption Configuration
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    raise ValueError(
        "ENCRYPTION_KEY must be set in .env. "
        "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
    )

try:
    cipher = Fernet(ENCRYPTION_KEY.encode())
except Exception as e:
    raise ValueError(f"Invalid ENCRYPTION_KEY format: {e}")


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'), 
        hashed_password.encode('utf-8')
    )


def hash_password(password: str) -> str:
    """Hash a password using bcrypt with optimized rounds for performance"""
    # Using 10 rounds instead of default 12 for better performance
    # Still secure but ~4x faster
    salt = bcrypt.gensalt(rounds=10)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[TokenData]:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        email: str = payload.get("email")
        
        if user_id_str is None:
            return None
        
        # Convert user_id from string to int
        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            return None
            
        return TokenData(user_id=user_id, email=email)
    except JWTError:
        return None


def encrypt_credentials(credentials: str) -> str:
    """Encrypt sensitive credentials using Fernet (AES-128)"""
    try:
        return cipher.encrypt(credentials.encode()).decode()
    except Exception as e:
        raise ValueError(f"Encryption failed: {e}")


def decrypt_credentials(encrypted: str) -> str:
    """Decrypt sensitive credentials"""
    try:
        return cipher.decrypt(encrypted.encode()).decode()
    except Exception as e:
        raise ValueError(f"Decryption failed: {e}")
