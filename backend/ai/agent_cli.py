"""Agent CLI 测试入口 - 手动验证 Agent 工作"""
import sys
import argparse
from pathlib import Path

# 把项目根目录加入 path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.ai.agent import StockAgent


def main():
    parser = argparse.ArgumentParser(description="衡势价值 Agent CLI")
    parser.add_argument("message", nargs="*", default=["你好"], help="用户消息")
    parser.add_argument("--max-steps", type=int, default=5, help="最大步数")
    args = parser.parse_args()

    user_message = " ".join(args.message)
    print(f"\n[用户] {user_message}\n")
    print("=" * 60)

    agent = StockAgent(max_steps=args.max_steps)
    for event in agent.run(user_message, history=[], session_id="cli-test"):
        event_type = event.event
        data = event.data

        if event_type == "thinking":
            print(f"\n💭 步骤 {data['step']}: 思考中...")
        elif event_type == "tool_call":
            print(f"\n🔧 调用 {data['name']}({data.get('args', {})})")
        elif event_type == "tool_result":
            icon = "✅" if data['status'] == "success" else "❌"
            print(f"{icon} {data['name']} 完成 ({data['duration_ms']}ms)")
            preview = data.get('result_preview', '')[:200]
            if preview:
                print(f"   预览: {preview}...")
        elif event_type == "final_answer":
            print(f"\n🤖 Agent:\n{data['content']}\n")
        elif event_type == "done":
            print(f"\n⏱️  总耗时 {data['duration_ms']}ms, 共 {data['step']} 步")
        elif event_type == "error":
            print(f"\n❌ 错误: {data['content']}")


if __name__ == "__main__":
    main()
