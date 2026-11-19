"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { EventSearch } from "@/components/EventSearch";
import { buildQuery, parseQuery } from "@/lib/api";

function SearchPage() {
  const router = useRouter();
  const params = useSearchParams();
  return (
    <EventSearch
      initialQuery={parseQuery(new URLSearchParams(params.toString()))}
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
