"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, Suspense, useState } from "react";

import { CosplayerList } from "@/components/CosplayerList";
import { Pagination } from "@/components/Pagination";
import { fetchCosplayers } from "@/lib/api";
import { useFetch } from "@/lib/useFetch";

function CosplayersContent() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const q = params.get("q") ?? "";
  const page = Math.max(1, Number(params.get("page")) || 1);
  const [draft, setDraft] = useState(q);
  const { data, error, loading } = useFetch(() => fetchCosplayers({ q, page }), params.toString());

  const navigate = (nextQ: string, nextPage: number) => {
    const query = new URLSearchParams();
    if (nextQ.trim()) query.set("q", nextQ.trim());
    if (nextPage > 1) query.set("page", String(nextPage));
    const qs = query.toString();
    router.push(qs ? `${pathname}?${qs}` : pathname);
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    navigate(draft, 1);
  };

  return (
    <>
      <h1>コスプレイヤーを探す</h1>
      <form className="search-form card" onSubmit={submit} role="search">
        <label className="field">
          キーワード
          <input
            type="search"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="名前・説明文・経歴"
          />
        </label>
        <div>
          <button type="submit">検索</button>
        </div>
      </form>
      {error && <p className="error">{error}</p>}
      {loading && <p className="muted">読み込み中…</p>}
      {data && !loading && (
        <>
          <p className="muted">{data.count} 人</p>
          <CosplayerList cosplayers={data.results} />
          <Pagination page={page} count={data.count} onChange={(p) => navigate(q, p)} />
        </>
      )}
    </>
  );
}

export default function CosplayersPage() {
  return (
    <Suspense fallback={<p className="muted">読み込み中…</p>}>
      <CosplayersContent />
    </Suspense>
  );
}
