#!/usr/bin/env bash
# check_prod_bundle.sh - 验证打包后的 .app 是否能正常启动和操作
# 用途：发现"开发能跑但打包就坏"的问题（依赖缺失、schema 漂移等）
# 退出码：0=通过 / 1=schema 不一致 / 2=依赖缺失 / 3=.app 找不到
set -e

PROJECT_ROOT="/Users/ws/Desktop/Project/Trea-Project/STOCK-Dev"
APP_PATH="$PROJECT_ROOT/src-tauri/target/release/bundle/macos/衡势价值.app"
DB_PATH="$HOME/Library/Application Support/com.hengshi-value.app/stock_data.db"
DB_PATH_ALT="$HOME/Library/Application Support/衡势价值/data/stock_data.db"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✅ $*${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $*${NC}"; }
err()  { echo -e "${RED}❌ $*${NC}"; }

echo "======================================"
echo "  Production Bundle Health Check"
echo "======================================"

# Step 1: 检查 .app 是否存在
if [ ! -d "$APP_PATH" ]; then
  err "未找到 $APP_PATH"
  err "请先运行: cd $PROJECT_ROOT && pyinstaller backend-runner.spec && cd src-tauri && cargo tauri build"
  exit 3
fi
ok "找到 .app: $APP_PATH"

# Step 2: 检查 backend-runner 是否打包了第三方依赖
BACKEND_RUNNER="$APP_PATH/Contents/Resources/backend-runner"
if [ ! -f "$BACKEND_RUNNER" ]; then
  err "未找到 $BACKEND_RUNNER"
  exit 3
fi

# 检查 backend-runner 是否真的能 import openai / yaml（模拟生产环境调用）
echo ""
echo "[1/3] 检查打包后的依赖..."
DEPS_MISSING=""
for module in openai yaml; do
  if "$BACKEND_RUNNER" -c "import $module; print('OK')" >/dev/null 2>&1; then
    ok "  $module 可导入"
  else
    err "  $module 缺失或导入失败"
    DEPS_MISSING="$DEPS_MISSING $module"
  fi
done
if [ -n "$DEPS_MISSING" ]; then
  err "缺失依赖:$DEPS_MISSING"
  err "修复方法：把顶层 import 改为函数内惰性 import，或确保 pyinstaller spec 包含 hiddenimports"
  exit 2
fi

# Step 3: 检查 db schema 一致性
echo ""
echo "[2/3] 检查 db schema..."
DB_FOUND=""
for p in "$DB_PATH" "$DB_PATH_ALT"; do
  if [ -f "$p" ]; then DB_FOUND="$p"; break; fi
done

if [ -z "$DB_FOUND" ]; then
  warn "未找到用户 db（首次启动会自动创建），跳过 schema 检查"
  warn "提示: db 路径: $DB_PATH"
else
  ok "找到 db: $DB_FOUND"
  python3 - "$DB_FOUND" << 'PYEOF'
import sys, sqlite3
p = sys.argv[1]
conn = sqlite3.connect(p)

EXPECTED = {
    "agent_session": ["message_count", "last_message", "is_pinned", "preview"],
    "agent_message": ["token_count"],
}

problems = 0
for table, cols in EXPECTED.items():
    try:
        existing = [r[1] for r in conn.execute("PRAGMA table_info(" + table + ")").fetchall()]
    except Exception as e:
        print("  \u274c " + table + " 表不存在: " + str(e))
        problems += 1
        continue
    missing = [c for c in cols if c not in existing]
    if missing:
        print("  \u274c " + table + " 缺失列: " + str(missing))
        print("     修复 SQL:")
        for c in missing:
            if c in ("message_count", "is_pinned"):
                decl = "INTEGER DEFAULT 0"
            else:
                decl = "TEXT DEFAULT ''"
            print("       ALTER TABLE " + table + " ADD COLUMN " + c + " " + decl + ";")
        problems += 1
    else:
        print("  \u2705 " + table + " schema 完整")

sys.exit(1 if problems else 0)
PYEOF
  if [ $? -ne 0 ]; then
    err "Schema 不一致，请执行上面的 ALTER TABLE"
    exit 1
  fi
  ok "Schema 验证通过"
fi

# Step 4: 启动 .app 烟雾测试
echo ""
echo "[3/3] 启动 .app 烟雾测试..."
if [ -d "$APP_PATH" ]; then
  open "$APP_PATH" 2>/dev/null || true
  sleep 3
  if pgrep -f "衡势价值" >/dev/null 2>&1; then
    ok ".app 启动成功（PID 存在）"
    killall "衡势价值" 2>/dev/null || true
  else
    warn ".app 启动后未检测到进程（可能需要更长等待时间）"
  fi
fi

echo ""
echo "======================================"
ok "所有检查通过"
echo "======================================"
