"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { EventList } from "@/components/EventList";
import { EventSearchForm, type EventSearchValues } from "@/components/EventSearchForm";
import { Pagination } from "@/components/Pagination";
import { fetchEvents } from "@/lib/api";
import { useFetch } from "@/lib/useFetch";

function EventsContent() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const values: EventSearchValues = {
    q: params.get("q") ?? "",
    from: params.get("from") ?? "",
    to: params.get("to") ?? "",
    prefecture: params.get("prefecture") ?? "",
  };
  const page = Math.max(1, Number(params.get("page")) || 1);
  const key = params.toString();

  const { data, error, loading } = useFetch(() => fetchEvents({ ...values, page }), key);

  // 検索条件は URL のクエリに反映し、共有・戻る操作で再現できるようにする
  const navigate = (next: Partial<EventSearchValues> & { page?: number }) => {
    const query = new URLSearchParams();
    for (const [k, v] of Object.entries({ ...values, page: undefined, ...next })) {
      if (v !== undefined && String(v) !== "" && !(k === "page" && v === 1)) query.set(k, String(v));
    }
    const qs = query.toString();
    router.push(qs ? `${pathname}?${qs}` : pathname);
  };

  return (
    <>
      <h1>イベントを探す</h1>
      <EventSearchForm key={key} initial={values} onSearch={(v) => navigate({ ...v, page: 1 })} />
      {error && <p className="error">{error}</p>}
      {loading && <p className="muted">読み込み中…</p>}
      {data && !loading && (
        <>
          <p className="muted">{data.count} 件</p>
          <EventList events={data.results} />
          <Pagination page={page} count={data.count} onChange={(p) => navigate({ page: p })} />
        </>
      )}
    </>
  );
}

export default function EventsPage() {
  return (
    <Suspense fallback={<p className="muted">読み込み中…</p>}>
      <EventsContent />
    </Suspense>
  );
}
