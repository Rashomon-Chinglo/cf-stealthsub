"""TOTP verification utilities."""

import pyotp


def verify_totp(code: str, secret: str) -> bool:
    """Verify a TOTP code against the secret.

    Allows ±1 time window (±30s) for clock drift tolerance.
    """
    try:
        return pyotp.TOTP(secret).verify(code, valid_window=1)
    except Exception:
        return False


def generate_provisioning_uri(secret: str) -> str:
    """Generate otpauth:// URI for QR code scanning."""
    return pyotp.TOTP(secret).provisioning_uri(
        name="CFOptimizer", issuer_name="CF-IP-Opt"
    )
