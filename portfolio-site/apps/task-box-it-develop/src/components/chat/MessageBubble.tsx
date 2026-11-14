import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { splitContent } from "@/lib/html-mock";
import type { ChatMessage } from "@/lib/types";
import { HtmlMockPreview } from "./HtmlMockPreview";

export const ESTIMATE_NOTICE = "AIによる自動的な見積もりです";
export const PREVIEW_NOTICE = "仮の値を含むプレビューです";

type Props = { message: Pick<ChatMessage, "role" | "kind" | "content" | "metadata"> };

export function MessageBubble({ message }: Props) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <p className="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl rounded-br-md bg-amber-500 px-4 py-2.5 text-[15px] leading-relaxed text-white">
          {message.content}
        </p>
      </div>
    );
  }

  const { metadata } = message;
  const completed = metadata.completed_items ?? [];
  return (
    <div className="flex justify-start">
      <div className="max-w-[92%] space-y-2 rounded-2xl rounded-bl-md bg-white px-4 py-3 text-[15px] leading-relaxed text-stone-800 shadow-sm ring-1 ring-stone-200">
        {message.kind === "agent_result" && (
          <p className="text-xs font-bold text-amber-700">{metadata.agent_name}</p>
        )}
        {/* 注意書きはAIに書かせず、画面が固定で付ける */}
        {metadata.is_estimate && (
          <p className="rounded-lg bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-800">⚠️ {ESTIMATE_NOTICE}</p>
        )}
        {metadata.is_preview && (
          <p className="rounded-lg bg-sky-50 px-3 py-1.5 text-xs font-medium text-sky-800">📝 {PREVIEW_NOTICE}</p>
        )}
        {completed.length > 0 && (
          <p className="text-xs text-stone-500">
            まだ決まっていないため、仮の値を入れた項目: {completed.join("、")}
          </p>
        )}
        {splitContent(message.content).map((part, index) =>
          part.type === "html" ? (
            <HtmlMockPreview key={index} html={part.html} />
          ) : (
            // react-markdown は生のHTMLを解釈しない（rehype-raw を入れないこと）
            <div key={index} className="md break-words">
              <Markdown remarkPlugins={[remarkGfm]}>{part.text}</Markdown>
            </div>
          ),
        )}
      </div>
    </div>
  );
}
