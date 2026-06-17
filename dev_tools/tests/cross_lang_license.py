#!/usr/bin/env python3
"""Cross-language License key test

Generates 3 keys via license_gen.py and verifies each against the
same CRC32 algorithm used by Rust's parse_license_key.
"""
import subprocess
import binascii
import sys


def parse_rust_style(key: str):
    """Mirror Rust parse_license_key CRC32 logic."""
    parts = key.strip().split("-")
    assert len(parts) == 6, f"expected 6 parts, got {len(parts)}"
    assert parts[0] == "HSP", f"bad prefix: {parts[0]}"
    body = f"HSP-{parts[1]}-{parts[2]}-{parts[3]}-{parts[4]}"
    crc = binascii.crc32(body.encode("ascii")) & 0xFFFFFFFF
    expected = f"{(~crc & 0xFFFF):04X}"
    return parts[1], parts[5].upper() == expected.upper()


def main():
    keys = []
    for tier in ("FREE", "PRO", "VIP"):
        r = subprocess.run(
            ["python3", "backend/stock-analyst/scripts/license_gen.py", tier, "30"],
            capture_output=True, text=True, cwd=".",
        )
        for line in r.stdout.splitlines():
            if "Key:" in line:
                key = line.split("Key:")[1].strip()
                keys.append((tier, key))
                break

    # KAT for standard CRC32-IEEE
    kat = binascii.crc32(b"123456789") & 0xFFFFFFFF
    assert kat == 0xCBF43926, f"CRC32 KAT failed: {kat:08X}"
    print(f"[OK] CRC32 KAT (b'123456789' = 0xCBF43926): {kat:08X}")

    all_ok = True
    for tier, key in keys:
        parsed_tier, crc_ok = parse_rust_style(key)
        ok = crc_ok and parsed_tier == tier
        all_ok &= ok
        print(f"[{'OK' if ok else 'FAIL'}] {tier}: {key}")
        print(f"       parsed_tier={parsed_tier}, CRC32 match={crc_ok}")

    if all_ok:
        print("\n[OK] All 3 cross-lang License keys parse correctly")
        return 0
    else:
        print("\n[FAIL] Some keys failed cross-lang check")
        return 1


if __name__ == "__main__":
    sys.exit(main())
