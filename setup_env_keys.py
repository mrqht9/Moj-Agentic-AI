#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Setup .env file with security keys
"""

import secrets
from cryptography.fernet import Fernet
from pathlib import Path

# Generate keys
jwt_secret = secrets.token_urlsafe(64)
encryption_key = Fernet.generate_key().decode()

# Read existing .env or create new
env_file = Path(".env")
env_lines = []

if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        env_lines = f.readlines()

# Update or add keys
jwt_found = False
enc_found = False
new_lines = []

for line in env_lines:
    if line.startswith('JWT_SECRET_KEY='):
        new_lines.append(f'JWT_SECRET_KEY={jwt_secret}\n')
        jwt_found = True
    elif line.startswith('ENCRYPTION_KEY='):
        new_lines.append(f'ENCRYPTION_KEY={encryption_key}\n')
        enc_found = True
    else:
        new_lines.append(line)

# Add if not found
if not jwt_found:
    new_lines.append(f'\n# Security Keys - Generated automatically\n')
    new_lines.append(f'JWT_SECRET_KEY={jwt_secret}\n')

if not enc_found:
    new_lines.append(f'ENCRYPTION_KEY={encryption_key}\n')

# Write back
with open(env_file, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ تم تحديث ملف .env بنجاح!")
print()
print("المفاتيح المولدة:")
print(f"JWT_SECRET_KEY={jwt_secret}")
print(f"ENCRYPTION_KEY={encryption_key}")
print()
print("⚠️ احفظ هذه المفاتيح في مكان آمن!")
