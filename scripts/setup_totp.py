"""Generate TOTP secret and provisioning URI for Authenticator app setup."""

from __future__ import annotations

import pyotp


def main() -> None:
    secret = pyotp.random_base32()
    uri = pyotp.TOTP(secret).provisioning_uri(
        name="CFStealthSub", issuer_name="CF-StealthSub"
    )

    print()
    print("=" * 50)
    print("  CF StealthSub — TOTP Setup")
    print("=" * 50)
    print()
    print("  Secret (paste into config.yaml):")
    print(f"    {secret}")
    print()
    print("  Provisioning URI (for QR code):")
    print(f"    {uri}")
    print()
    print("  Steps:")
    print("  1. Copy the secret above into config.yaml → auth.totp_secret")
    print("  2. Scan the QR code or manually add the secret to your")
    print("     Authenticator app (Google Authenticator, Authy, etc.)")
    print()
    print("=" * 50)


if __name__ == "__main__":
    main()
