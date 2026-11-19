"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { EventSearch } from "@/components/EventSearch";
import { buildQuery, parseQuery } from "@/lib/api";

function SearchPage() {
  const router = useRouter();
  const params = useSearchParams();
  const query = parseQuery(new URLSearchParams(params.toString()));
  // URL（ヘッダーのリンク・ブラウザの戻る）が変わったらフォームごと作り直して URL に合わせる
  return (
    <EventSearch
      key={buildQuery(query).toString()}
      query={query}
      onQueryChange={(q) => {
        const qs = buildQuery(q).toString();
        router.replace(qs ? `/?${qs}` : "/", { scroll: false });
      }}
    />
  );
}

export default function Home() {
  return (
    <>
      <h1>イベントを探す</h1>
      <Suspense fallback={<p className="muted">読み込み中…</p>}>
        <SearchPage />
      </Suspense>
    </>
  );
}
