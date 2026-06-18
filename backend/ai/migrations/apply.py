"""数据库 migration 应用器"""
import sqlite3
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent


def apply_migrations(db_path: str) -> None:
    """应用所有未执行的 migration"""
    conn = sqlite3.connect(db_path)
    try:
        # 确保 _migrations 表存在
        conn.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at DATETIME DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.commit()

        # 找到所有 .sql 文件，按名称排序
        sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

        for sql_file in sql_files:
            # 检查是否已应用
            cursor = conn.execute(
                "SELECT 1 FROM _migrations WHERE name = ?", (sql_file.name,)
            )
            if cursor.fetchone():
                continue

            # 应用
            sql = sql_file.read_text(encoding="utf-8")
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO _migrations (name) VALUES (?)", (sql_file.name,)
            )
            conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    # 直接运行：python apply.py /path/to/db
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else "stock_data.db"
    apply_migrations(db_path)
    print(f"✅ Migration applied to {db_path}")
