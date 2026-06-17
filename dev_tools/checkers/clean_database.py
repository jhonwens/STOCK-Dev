#!/usr/bin/env python3
"""数据库清理脚本

清理项：
1. 删除空表 stock_pattern 和 stock_chan_theory
2. 清空 stock_alert 表（预警功能已从产品中移除）
3. VACUUM 压缩数据库，回收空间
"""
import sqlite3
import sys
from pathlib import Path

DB = Path("backend/stock-analyst/data/stock_data.db")


def main():
    if not DB.exists():
        print(f"[SKIP] {DB} 不存在")
        return 0

    size_before = DB.stat().st_size / 1024 / 1024
    print(f"[INFO] 数据库初始大小: {size_before:.2f} MB")

    con = sqlite3.connect(DB)
    cur = con.cursor()

    # 1. 删除空表
    for t in ("stock_pattern", "stock_chan_theory"):
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,))
        if cur.fetchone():
            cur.execute(f"DROP TABLE {t}")
            print(f"[OK] 删除空表: {t}")
        else:
            print(f"[SKIP] 表 {t} 不存在")

    # 2. 清空 stock_alert（预警功能已移除）
    cur.execute("SELECT COUNT(*) FROM stock_alert")
    n = cur.fetchone()[0]
    if n > 0:
        cur.execute("DELETE FROM stock_alert")
        print(f"[OK] 清空 stock_alert: {n} 行")
        # 重置自增
        cur.execute("DELETE FROM sqlite_sequence WHERE name='stock_alert'")
    else:
        print("[SKIP] stock_alert 已为空")

    con.commit()

    # 3. VACUUM 必须在事务外执行，需要重新连接
    con.close()
    con = sqlite3.connect(DB)
    con.isolation_level = None  # autocommit mode
    cur = con.cursor()
    cur.execute("VACUUM")
    print("[OK] VACUUM 压缩完成")
    con.close()

    size_after = DB.stat().st_size / 1024 / 1024
    saved = size_before - size_after
    print(f"\n[INFO] 清理前: {size_before:.2f} MB → 清理后: {size_after:.2f} MB (节省 {saved:.2f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
