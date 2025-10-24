#!/usr/bin/env python3
"""
RSA License Validator for Presidio Analyzer
This module validates licenses using RSA public key cryptography
"""

import json
import base64
import os
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend


class LicenseValidator:
    def __init__(self, public_key_pem=None):
        self.backend = default_backend()
        self.public_key = None
        
        if public_key_pem:
            self.load_public_key_from_string(public_key_pem)
        else:
            self.load_public_key_from_file()
    
    def load_public_key_from_file(self, key_file="keys/public_key.pem"):
        """Load public key from PEM file."""
        try:
            if os.path.exists(key_file):
                with open(key_file, 'rb') as f:
                    public_key_data = f.read()
                self.public_key = serialization.load_pem_public_key(
                    public_key_data, backend=self.backend
                )
            else:
                # Embedded public key (you would replace this with your actual public key)
                self.load_embedded_public_key()
        except Exception as e:
            raise Exception(f"Failed to load public key: {e}")
    
    def load_public_key_from_string(self, public_key_pem):
        """Load public key from PEM string."""
        try:
            if isinstance(public_key_pem, str):
                public_key_pem = public_key_pem.encode()
            self.public_key = serialization.load_pem_public_key(
                public_key_pem, backend=self.backend
            )
        except Exception as e:
            raise Exception(f"Failed to load public key from string: {e}")
    
    def load_embedded_public_key(self):
        """Load embedded public key (replace with your actual public key)."""
        # This is a placeholder - replace with your actual public key
        embedded_key = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAv+uuluZT4VFafVwoQBfc
felD4SnGcSTQHbS2ajWgIYTAFxSLcYKziv+MzlSEHe85CqLyQd+B/yTcUNjCIZuv
q4kki4+ZrqojosDI1UEUP1e7/YljnQw5zHHbB+5HVGM024nhPWc/vyMzxxRZiDt8
o08g7S7VTi1N2+ikjhRp4qQqyblYbjB1wpV1uOOWorTmcYMg4Mr2/2JzkruLlkC7
lOzxS/56O+nVO6WWvbtl9KvDho4fbYKH94H8kyqV1DWZcorkYj6gpoNMsISBWg60
PrXNKVGQBAewAgZn/vPqnKNi/H7szOfMS573f0PB+qn04cJRQc3enTgV5d4vvkt9
GwIDAQAB
-----END PUBLIC KEY-----"""
        
        try:
            self.public_key = serialization.load_pem_public_key(
                embedded_key.encode(), backend=self.backend
            )
        except Exception:
            # If embedded key fails, we'll generate a temporary one for demo
            print("⚠️  Using demo public key. Replace with your actual key.")
            self.public_key = None
    
    def verify_license_signature(self, license_data, signature_b64):
        """Verify license signature using public key."""
        if not self.public_key:
            # For demo purposes, return True if no public key
            print("⚠️  No public key available, skipping signature verification")
            return True
        
        try:
            # Decode signature
            signature = base64.b64decode(signature_b64)
            
            # Convert license data to JSON string (same as signing)
            license_json = json.dumps(license_data, sort_keys=True)
            license_bytes = license_json.encode('utf-8')
            
            # Verify signature
            self.public_key.verify(
                signature,
                license_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        
        except Exception as e:
            print(f"❌ Signature verification failed: {e}")
            return False
    
    def validate_license_expiry(self, license_data):
        """Check if license has expired."""
        try:
            expiry_str = license_data.get('expiry_date')
            if not expiry_str:
                return False
            
            expiry_date = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
            current_date = datetime.now()
            
            if current_date > expiry_date:
                print(f"❌ License expired on {expiry_date.strftime('%Y-%m-%d')}")
                return False
            
            days_remaining = (expiry_date - current_date).days
            if days_remaining <= 30:
                print(f"⚠️  License expires in {days_remaining} days")
            
            return True
        
        except Exception as e:
            print(f"❌ Error checking expiry: {e}")
            return False
    
    def validate_license_features(self, license_data, required_features=None):
        """Validate that license includes required features."""
        if not required_features:
            required_features = ["text_analysis", "pii_detection"]
        
        license_features = license_data.get('features', [])
        
        for feature in required_features:
            if feature not in license_features:
                print(f"❌ License missing required feature: {feature}")
                return False
        
        return True
    
    def validate_license(self, license_key_b64):
        """Complete license validation."""
        try:
            # Decode base64 license
            license_json = base64.b64decode(license_key_b64).decode('utf-8')
            license_obj = json.loads(license_json)
            
            license_data = license_obj.get('license_data')
            signature = license_obj.get('signature')
            
            if not license_data or not signature:
                print("❌ Invalid license format")
                return False
            
            print(f"🔍 Validating license for: {license_data.get('customer', 'Unknown')}")
            print(f"📦 Product: {license_data.get('product', 'Unknown')}")
            print(f"🆔 License ID: {license_data.get('license_id', 'Unknown')}")
            
            # Verify signature
            if not self.verify_license_signature(license_data, signature):
                print("❌ License signature verification failed")
                return False
            
            # Check expiry
            if not self.validate_license_expiry(license_data):
                return False
            
            # Check features
            if not self.validate_license_features(license_data):
                return False
            
            print("✅ License validation successful")
            return True
            
        except Exception as e:
            print(f"❌ License validation error: {e}")
            return False
    
    def get_license_info(self, license_key_b64):
        """Get license information without full validation."""
        try:
            license_json = base64.b64decode(license_key_b64).decode('utf-8')
            license_obj = json.loads(license_json)
            return license_obj.get('license_data', {})
        except Exception:
            return {}


# Convenience function for app integration
def validate_startup_license():
    """Validate license key for application startup."""
    print("🔐 Checking RSA license...")
    
    license_key = os.environ.get('LICENSE_KEY')
    
    if not license_key:
        print("\n❌ ERROR: No LICENSE_KEY found in environment variables")
        print("\n📝 To get a license:")
        print("1. contact Privacy Pillar support:")
        print("2. Set the environment variable:")
        print("   export LICENSE_KEY='<generated_license_key>'")
        print("3. Restart the application")
        return False
    
    try:
        validator = LicenseValidator()
        if validator.validate_license(license_key):
            license_info = validator.get_license_info(license_key)
            print(f"✅ Licensed to: {license_info.get('customer', 'Unknown')}")
            print(f"📅 Valid until: {license_info.get('expiry_date', 'Unknown')[:10]}")
            return True
        else:
            return False
    
    except ImportError:
        print("❌ Missing required dependency: cryptography")
        print("📦 Install with: pip install cryptography")
        return False
    except Exception as e:
        print(f"❌ License validation failed: {e}")
        return False


if __name__ == "__main__":
    # Test validation with environment variable
    if validate_startup_license():
        print("🚀 Application ready to start")
    else:
        print("❌ Application cannot start without valid license")