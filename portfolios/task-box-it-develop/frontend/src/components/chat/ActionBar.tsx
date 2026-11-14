"use client";

export type ActionKey = "finalize" | "market-estimate" | "self-estimate" | "summary-download" | "clear";

// ボタン名は requirements.md（ストーリー7 基準6）の表記どおりとする
export const ACTIONS: { key: ActionKey; label: string; primary?: boolean }[] = [
  { key: "finalize", label: "要件の確定", primary: true },
  { key: "market-estimate", label: "相場見積もり" },
  { key: "self-estimate", label: "自分見積もり" },
  { key: "summary-download", label: "現状の要約のDL" },
  { key: "clear", label: "クリア" },
];

export function ActionBar({ disabled, onAction }: { disabled: boolean; onAction: (key: ActionKey) => void }) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-1">
      {ACTIONS.map((action) => (
        <button
          key={action.key}
          type="button"
          disabled={disabled}
          onClick={() => onAction(action.key)}
          className={
            "shrink-0 rounded-full px-4 py-2 text-sm font-medium transition disabled:opacity-40 " +
            (action.primary
              ? "bg-red-600 text-white hover:bg-red-700"
              : "border border-stone-300 bg-white text-stone-700 hover:bg-stone-100")
          }
        >
          {action.label}
        </button>
      ))}
    </div>
  );
}
