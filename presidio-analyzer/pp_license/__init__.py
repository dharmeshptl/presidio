"""
Presidio Analyzer License System
RSA-based license generation and validation
"""


from .license_validator import LicenseValidator, validate_startup_license

__all__ = [ 'LicenseValidator', 'validate_startup_license']