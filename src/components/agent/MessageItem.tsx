import { exportMessage } from "../../services/agent";

export interface ToolCall {
  name: string;
  args: Record<string, any>;
  status: "running" | "success" | "error";
  resultPreview?: string;
  durationMs?: number;
}

export interface Message {
  id: number;
  sessionId: string;
  role: "user" | "assistant" | "tool";
  content: string;
  toolCalls?: ToolCall[];
  createdAt: string;
}

interface Props {
  message: Message;
}

export default function MessageItem({ message }: Props) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[70%] bg-blue-500 text-white px-4 py-2 rounded-lg">
          {message.content}
        </div>
      </div>
    );
  }

  if (message.role === "tool") {
    return (
      <div className="mb-2">
        {message.toolCalls?.map((tc, i) => (
          <div key={i} className="bg-purple-50 border border-purple-200 rounded p-2 mb-1 text-sm">
            <div className="flex items-center gap-2">
              <span>🔧</span>
              <span className="font-mono">{tc.name}</span>
              <span className="text-gray-500 text-xs">({JSON.stringify(tc.args)})</span>
              <span className="ml-auto">
                {tc.status === "running" && "⏳"}
                {tc.status === "success" && "✅"}
                {tc.status === "error" && "❌"}
                {tc.durationMs && <span className="text-xs text-gray-400 ml-1">{tc.durationMs}ms</span>}
              </span>
            </div>
            {tc.resultPreview && (
              <pre className="mt-1 text-xs text-gray-600 whitespace-pre-wrap">
                {tc.resultPreview}
              </pre>
            )}
          </div>
        ))}
      </div>
    );
  }

  if (message.role === "assistant" && message.id > 0) {
    return (
      <div className="flex justify-start mb-4">
        <div className="max-w-[80%] bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2 text-sm text-gray-500">
            <span>🤖</span>
            <span>Agent</span>
            <div className="ml-auto flex gap-2">
              <button
                onClick={async () => {
                  try {
                    const path = await exportMessage(message.sessionId, message.id, "md");
                    alert(`已保存: ${path}`);
                  } catch (e) {
                    alert(`保存失败: ${e}`);
                  }
                }}
                className="text-xs px-2 py-1 rounded bg-gray-100 hover:bg-gray-200"
              >
                💾 MD
              </button>
              <button
                onClick={async () => {
                  try {
                    const path = await exportMessage(message.sessionId, message.id, "html");
                    alert(`已保存: ${path}`);
                  } catch (e) {
                    alert(`保存失败: ${e}`);
                  }
                }}
                className="text-xs px-2 py-1 rounded bg-gray-100 hover:bg-gray-200"
              >
                🌐 HTML
              </button>
            </div>
          </div>
          <div className="prose prose-sm max-w-none whitespace-pre-wrap">
            {message.content}
          </div>
        </div>
      </div>
    );
  }

  // assistant (临时消息 id <= 0)
  return (
    <div className="flex justify-start mb-4">
      <div className="max-w-[80%] bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2 text-sm text-gray-500">
          <span>🤖</span>
          <span>Agent</span>
        </div>
        <div className="prose prose-sm max-w-none whitespace-pre-wrap">
          {message.content}
        </div>
      </div>
    </div>
  );
}
