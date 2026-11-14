"use client";

import type { AgentCall, SummaryDraft } from "@/lib/types";
import { Modal, primaryButton, secondaryButton } from "./Modal";

type AgentCallProps = { call: AgentCall; disabled: boolean; onAnswer: (approve: boolean) => void };

/** 入力を起点とするエージェントの呼び出しは、必ず依頼者の許可を取る。 */
export function AgentCallDialog({ call, disabled, onAnswer }: AgentCallProps) {
  return (
    <Modal title="確認">
      <p className="text-sm leading-relaxed text-stone-700">
        「<strong>{call.agent_name}</strong>」を実行してもいいですか？
        <br />
        これまでのお話をもとに作成します。少し時間がかかります。
      </p>
      <div className="flex justify-end gap-2">
        <button type="button" disabled={disabled} className={secondaryButton} onClick={() => onAnswer(false)}>
          いいえ
        </button>
        <button type="button" disabled={disabled} className={primaryButton} onClick={() => onAnswer(true)}>
          はい
        </button>
      </div>
    </Modal>
  );
}

export type FinalizeState =
  | { kind: "missing"; missing: string[] }
  | { kind: "summary"; summary: SummaryDraft }
  | { kind: "submitted"; notice: string };

type FinalizeProps = {
  state: FinalizeState;
  disabled: boolean;
  error: string;
  onSubmit: (summary: SummaryDraft) => void;
  onClose: () => void;
};

export function FinalizeDialog({ state, disabled, error, onSubmit, onClose }: FinalizeProps) {
  if (state.kind === "missing") {
    return (
      <Modal title="まだ決まっていない項目があります">
        <p className="text-sm text-stone-700">次の項目について、もう少しお話を聞かせてください。</p>
        <ul className="list-disc space-y-1 pl-6 text-sm font-medium text-stone-900">
          {state.missing.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <div className="flex justify-end">
          <button type="button" className={primaryButton} onClick={onClose}>
            お話を続ける
          </button>
        </div>
      </Modal>
    );
  }
  if (state.kind === "submitted") {
    return (
      <Modal title="送信しました">
        <p className="text-sm leading-relaxed text-stone-700">{state.notice}</p>
        <div className="flex justify-end">
          <button type="button" className={primaryButton} onClick={onClose}>
            閉じる
          </button>
        </div>
      </Modal>
    );
  }
  return (
    <Modal title={state.summary.title}>
      <p className="text-sm text-stone-600">この内容で送ってよければ「確定」を押してください。</p>
      {/* 確認用のため、マークダウンはレンダーせずテキストのまま見せる */}
      <pre className="min-h-0 flex-1 overflow-auto whitespace-pre-wrap break-words rounded-xl bg-stone-50 p-4 text-xs leading-relaxed text-stone-800">
        {state.summary.body_markdown}
      </pre>
      {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
      <div className="flex justify-end gap-2">
        <button type="button" disabled={disabled} className={secondaryButton} onClick={onClose}>
          修正
        </button>
        <button type="button" disabled={disabled} className={primaryButton} onClick={() => onSubmit(state.summary)}>
          確定
        </button>
      </div>
    </Modal>
  );
}

export function ClearConfirmDialog({ onConfirm, onCancel }: { onConfirm: () => void; onCancel: () => void }) {
  return (
    <Modal title="これまでのお話を消しますか？">
      <p className="text-sm leading-relaxed text-stone-700">
        消したお話は元に戻せません。すでに送信した内容は消えません。
        <br />
        また、1か月お話がないと、自動的に消えます。
      </p>
      <div className="flex justify-end gap-2">
        <button type="button" className={secondaryButton} onClick={onCancel}>
          やめる
        </button>
        <button type="button" className={primaryButton} onClick={onConfirm}>
          消す
        </button>
      </div>
    </Modal>
  );
}
