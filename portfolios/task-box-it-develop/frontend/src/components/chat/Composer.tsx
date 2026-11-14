"use client";

import type { PromptTemplate } from "@/lib/types";

export const MESSAGE_MAX_LENGTH = 4000;

type Props = {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  templates: PromptTemplate[];
  disabled: boolean;
};

export function Composer({ value, onChange, onSend, templates, disabled }: Props) {
  const canSend = !disabled && value.trim().length > 0 && value.length <= MESSAGE_MAX_LENGTH;
  return (
    <form
      className="space-y-2"
      onSubmit={(event) => {
        event.preventDefault();
        if (canSend) onSend();
      }}
    >
      <select
        aria-label="テンプレ"
        value=""
        disabled={disabled || templates.length === 0}
        onChange={(event) => {
          // テンプレはテキストボックスに入れるだけで、送信はしない（送る前に書き換えられる）
          const template = templates.find((t) => String(t.id) === event.target.value);
          if (template) onChange(template.prompt);
        }}
        className="w-full rounded-full border border-stone-300 bg-white px-4 py-2 text-sm text-stone-700 disabled:opacity-50"
      >
        <option value="">💡 テンプレから選ぶ</option>
        {templates.map((template) => (
          <option key={template.id} value={template.id}>
            {template.label}
          </option>
        ))}
      </select>
      <div className="flex items-end gap-2">
        <textarea
          aria-label="メッセージ"
          value={value}
          disabled={disabled}
          rows={2}
          placeholder="作りたいもの、困っていることを気軽にどうぞ"
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && canSend) onSend();
          }}
          className="max-h-40 min-h-[3.25rem] flex-1 resize-y rounded-2xl border border-stone-300 bg-white px-4 py-3 text-[15px] outline-none focus:border-amber-500 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!canSend}
          className="rounded-full bg-amber-500 px-5 py-3 text-sm font-bold text-white transition hover:bg-amber-600 disabled:opacity-40"
        >
          送信
        </button>
      </div>
      {value.length > MESSAGE_MAX_LENGTH && (
        <p role="alert" className="text-xs text-red-600">
          文章が長すぎます（{MESSAGE_MAX_LENGTH}文字まで）
        </p>
      )}
    </form>
  );
}
