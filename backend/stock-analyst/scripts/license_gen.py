#!/usr/bin/env python3
# 衡势价值 · 激活码生成器
# 用法: python license_gen.py <TIER> [DAYS]
# 例: python license_gen.py PRO 365
#
# 校验算法必须与 src-tauri/src/license.rs 中的 CRC32 实现保持一致：
#   1. 标准 CRC32-IEEE（多项式 0xEDB88320，初值 0xFFFFFFFF，反演输出）
#   2. 取结果低 16 位，格式化为 4 位大写 hex
#   3. 校验内容为 "HSP-{TIER}-{SEG1}-{SEG2}-{SEG3}"

import sys
import random
import string
import binascii
from datetime import datetime, timedelta

PREFIX = "HSP"
SEG_LEN = 4
CHARS = string.ascii_uppercase + string.digits


def crc16_check(body: str) -> str:
    """与 Rust 端 crc32() & 0xFFFF 保持一致"""
    crc = binascii.crc32(body.encode("ascii")) & 0xFFFFFFFF
    return f"{(~crc & 0xFFFF):04X}"


def gen_seg() -> str:
    return "".join(random.choices(CHARS, k=SEG_LEN))


def gen_key(tier: str) -> str:
    seg1, seg2, seg3 = gen_seg(), gen_seg(), gen_seg()
    body = f"{PREFIX}-{tier}-{seg1}-{seg2}-{seg3}"
    check = crc16_check(body)
    return f"{body}-{check}"


def main():
    if len(sys.argv) < 2:
        print("Usage: python license_gen.py <FREE|PRO|VIP> [DAYS]")
        print()
        print("Examples:")
        print("  python license_gen.py PRO 365   # PRO 一年期")
        print("  python license_gen.py VIP       # VIP 永不过期 (默认 3650 天)")
        print()
        print("Tiers:")
        print("  FREE  - 免费版")
        print("  PRO   - 专业版")
        print("  VIP   - 至尊版")
        sys.exit(1)

    tier = sys.argv[1].upper()
    if tier not in ("FREE", "PRO", "VIP"):
        print(f"Invalid tier: {tier} (must be FREE, PRO or VIP)")
        sys.exit(1)

    days = int(sys.argv[2]) if len(sys.argv) > 2 else 3650
    key = gen_key(tier)
    issued = datetime.now().strftime("%Y-%m-%d")
    expired = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

    print("=" * 56)
    print("  衡势价值 · 激活码")
    print("=" * 56)
    print(f"  Key:     {key}")
    print(f"  Tier:    {tier}")
    print(f"  Issued:  {issued}")
    print(f"  Expired: {expired}")
    print(f"  Days:    {days}")
    print("=" * 56)
    print()
    print("请在「会员中心 → 激活码兑换」输入上述 Key。")
    print()


if __name__ == "__main__":
    main()
