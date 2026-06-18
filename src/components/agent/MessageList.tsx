import { useEffect, useRef } from "react";
import MessageItem, { Message, ToolCall } from "./MessageItem";

export type { Message };

interface Props {
  messages: Message[];
  streamingContent?: string;
  activeToolCalls?: ToolCall[];
}

export default function MessageList({ messages, streamingContent, activeToolCalls }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent, activeToolCalls]);

  return (
    <div className="flex-1 overflow-y-auto p-4 bg-gray-50">
      {messages.map((m) => (
        <MessageItem key={m.id} message={m} />
      ))}

      {activeToolCalls && activeToolCalls.length > 0 && (
        <div className="mb-2">
          {activeToolCalls.map((tc, i) => (
            <div key={i} className="bg-purple-50 border border-purple-200 rounded p-2 mb-1 text-sm">
              <div className="flex items-center gap-2">
                <span>🔧</span>
                <span className="font-mono">{tc.name}</span>
                <span className="text-gray-500 text-xs">({JSON.stringify(tc.args)})</span>
                <span className="ml-auto">
                  {tc.status === "running" && <span className="animate-pulse">⏳</span>}
                  {tc.status === "success" && "✅"}
                  {tc.status === "error" && "❌"}
                  {tc.durationMs && <span className="text-xs text-gray-400 ml-1">{tc.durationMs}ms</span>}
                </span>
              </div>
              {tc.resultPreview && (
                <pre className="mt-1 text-xs text-gray-600 whitespace-pre-wrap max-h-32 overflow-y-auto">
                  {tc.resultPreview}
                </pre>
              )}
            </div>
          ))}
        </div>
      )}

      {streamingContent && (
        <div className="flex justify-start">
          <div className="max-w-[80%] bg-white border border-gray-200 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2 text-sm text-gray-500">
              <span>🤖</span>
              <span>Agent</span>
            </div>
            <div className="prose prose-sm max-w-none whitespace-pre-wrap">
              {streamingContent}
              <span className="inline-block animate-pulse">▍</span>
            </div>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
