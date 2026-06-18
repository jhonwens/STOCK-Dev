import { useState, useRef } from "react";

interface Props {
  onSend: (text: string) => void;
  disabled?: boolean;
}

const EXAMPLES = [
  "688256 现在能买吗？",
  "我的持仓怎么样？",
  "推荐 5 只长期价值股",
  "半导体行业前景如何？",
  "今天大盘情绪怎样？",
  "寒武纪 300750 是什么股票？",
];

export default function InputBox({ onSend, disabled }: Props) {
  const [text, setText] = useState("");
  const [showExamples, setShowExamples] = useState(false);

  function handleSend() {
    if (!text.trim() || disabled) return;
    onSend(text.trim());
    setText("");
  }

  return (
    <div className="border-t bg-white p-3">
      <div className="flex gap-2 mb-2">
        <button
          onClick={() => setShowExamples(!showExamples)}
          className="text-xs px-2 py-1 rounded bg-gray-100 hover:bg-gray-200"
        >
          💡 示例问题
        </button>
      </div>
      {showExamples && (
        <div className="mb-2 flex flex-wrap gap-1">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => {
                setText(ex);
                setShowExamples(false);
              }}
              className="text-xs px-2 py-1 rounded bg-blue-50 text-blue-700 hover:bg-blue-100"
            >
              {ex}
            </button>
          ))}
        </div>
      )}
      <div className="flex gap-2">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder="输入你的问题... (Enter 发送, Shift+Enter 换行)"
          disabled={disabled}
          className="flex-1 px-3 py-2 border border-gray-300 rounded resize-none focus:outline-none focus:border-blue-500"
          rows={2}
        />
        <button
          onClick={handleSend}
          disabled={disabled || !text.trim()}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
        >
          发送 ➤
        </button>
      </div>
    </div>
  );
}
