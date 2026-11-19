"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { EventDetail } from "@/components/EventDetail";

function Detail() {
  const id = Number(useSearchParams().get("id"));
  if (!Number.isInteger(id) || id <= 0) {
    return <p className="alert">イベントが指定されていません。</p>;
  }
  return <EventDetail id={id} />;
}

export default function EventPage() {
  return (
    <>
      <p>
        <Link href="/">← 検索に戻る</Link>
      </p>
      <Suspense fallback={<p className="muted">読み込み中…</p>}>
        <Detail />
      </Suspense>
    </>
  );
}
