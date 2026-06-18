import { useEffect, useRef } from "react";
import MessageItem, { Message } from "./MessageItem";

export type { Message };

interface Props {
  messages: Message[];
  streamingContent?: string;
}

export default function MessageList({ messages, streamingContent }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  return (
    <div className="flex-1 overflow-y-auto p-4 bg-gray-50">
      {messages.map((m) => (
        <MessageItem key={m.id} message={m} />
      ))}
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
