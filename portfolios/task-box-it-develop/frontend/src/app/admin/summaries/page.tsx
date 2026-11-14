"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/AuthProvider";
import { STATUS_STYLES, formatDateTime } from "@/lib/admin";
import { ApiError, api } from "@/lib/api";
import { type AdminSummary, HANDLING_STATUS_LABELS, type HandlingStatus } from "@/lib/types";

type ListResponse = { count: number; next: string | null; previous: string | null; results: AdminSummary[] };

function SummaryList() {
  const [status, setStatus] = useState<HandlingStatus | "">("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<ListResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    const query = new URLSearchParams({ page: String(page) });
    if (status) query.set("handling_status", status);
    api<ListResponse>(`/admin/summaries/?${query}`)
      .then((response) => active && setData(response))
      .catch((cause) => active && setError(cause instanceof ApiError ? cause.message : "読み込めませんでした"));
    return () => {
      active = false;
    };
  }, [status, page]);

  return (
    <div className="mx-auto w-full max-w-4xl flex-1 overflow-y-auto px-4 py-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-bold text-stone-900">届いた要件サマリー</h1>
        <select
          aria-label="対応状況で絞り込む"
          value={status}
          onChange={(event) => {
            setStatus(event.target.value as HandlingStatus | "");
            setPage(1);
          }}
          className="rounded-full border border-stone-300 bg-white px-4 py-2 text-sm"
        >
          <option value="">すべての対応状況</option>
          {Object.entries(HANDLING_STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {error && <p role="alert" className="mt-4 text-sm text-red-600">{error}</p>}
      {data && data.results.length === 0 && <p className="mt-8 text-center text-sm text-stone-500">該当する要件サマリーはありません。</p>}

      <ul className="mt-4 space-y-2">
        {data?.results.map((summary) => (
          <li key={summary.id}>
            <Link
              href={`/admin/summaries/${summary.id}`}
              className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-2xl bg-white px-4 py-3 shadow-sm ring-1 ring-stone-200 transition hover:ring-amber-400"
            >
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${STATUS_STYLES[summary.handling_status]}`}>
                {HANDLING_STATUS_LABELS[summary.handling_status]}
              </span>
              <span className="min-w-0 flex-1 basis-48 truncate font-medium text-stone-900">{summary.title}</span>
              <span className="text-sm text-stone-600">{summary.user_name}</span>
              <span className="text-sm text-stone-500">{formatDateTime(summary.submitted_at)}</span>
              {summary.mail_status === "failed" && (
                <span className="rounded-full bg-red-600 px-2.5 py-0.5 text-xs font-bold text-white">メール送信失敗</span>
              )}
            </Link>
          </li>
        ))}
      </ul>

      {data && (data.previous || data.next) && (
        <div className="mt-4 flex justify-center gap-2 text-sm">
          <button type="button" disabled={!data.previous} onClick={() => setPage(page - 1)} className="rounded-full border border-stone-300 px-4 py-1.5 disabled:opacity-40">
            前へ
          </button>
          <button type="button" disabled={!data.next} onClick={() => setPage(page + 1)} className="rounded-full border border-stone-300 px-4 py-1.5 disabled:opacity-40">
            次へ
          </button>
        </div>
      )}
    </div>
  );
}

export default function AdminSummariesPage() {
  return (
    <RequireAuth admin>
      <SummaryList />
    </RequireAuth>
  );
}
