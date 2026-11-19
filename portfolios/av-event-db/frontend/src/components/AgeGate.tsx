"use client";

import { useState, useSyncExternalStore, type ReactNode } from "react";

export const AGE_KEY = "av-event-db:age-confirmed";
const listeners = new Set<() => void>();

function read(): string | null {
  try {
    return localStorage.getItem(AGE_KEY);
  } catch {
    return null;
  }
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

function confirmAge() {
  try {
    localStorage.setItem(AGE_KEY, "yes");
  } catch {
    // 保存できない環境でも、このページの表示中は確認済みとして扱う
  }
  listeners.forEach((l) => l());
}

/** 18歳以上の確認が済むまで内容を表示しない（REQ-7）。 */
export function AgeGate({ children }: { children: ReactNode }) {
  // 静的出力時（サーバー側）は未確認として描画し、内容を HTML に含めない
  const stored = useSyncExternalStore(subscribe, read, () => null);
  const [confirmedHere, setConfirmedHere] = useState(false);
  const [denied, setDenied] = useState(false);

  if (stored === "yes" || confirmedHere) return <>{children}</>;

  if (denied) {
    return (
      <section className="card age-gate" role="alert">
        <h1>ご利用いただけません</h1>
        <p>このサイトは18歳未満の方はご利用いただけません。</p>
      </section>
    );
  }

  return (
    <section className="card age-gate" aria-labelledby="age-gate-title">
      <h1 id="age-gate-title">年齢確認</h1>
      <p>このサイトはアダルト作品に出演する方のイベント情報を掲載しています。</p>
      <p>あなたは18歳以上ですか？</p>
      <div className="toolbar">
        <button
          type="button"
          className="button"
          onClick={() => {
            setConfirmedHere(true);
            confirmAge();
          }}
        >
          はい（18歳以上です）
        </button>
        <button type="button" className="button secondary" onClick={() => setDenied(true)}>
          いいえ（18歳未満です）
        </button>
      </div>
    </section>
  );
}
