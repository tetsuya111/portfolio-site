"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/AuthProvider";
import { formatDateTime } from "@/lib/admin";
import { ApiError, api } from "@/lib/api";
import { type AdminSummaryDetail, HANDLING_STATUS_LABELS, type HandlingStatus } from "@/lib/types";

function SummaryDetail() {
  const { id } = useParams<{ id: string }>();
  const [summary, setSummary] = useState<AdminSummaryDetail | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api<AdminSummaryDetail>(`/admin/summaries/${id}/`)
      .then((response) => active && setSummary(response))
      .catch((cause) => active && setError(cause instanceof ApiError ? cause.message : "読み込めませんでした"));
    return () => {
      active = false;
    };
  }, [id]);

  async function changeStatus(handling_status: HandlingStatus) {
    setSaving(true);
    setError("");
    try {
      setSummary(await api<AdminSummaryDetail>(`/admin/summaries/${id}/`, "PATCH", { handling_status }));
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "保存できませんでした");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-4xl flex-1 overflow-y-auto px-4 py-6">
      <Link href="/admin/summaries" className="text-sm text-stone-600 hover:text-stone-900">
        ← 一覧に戻る
      </Link>
      {error && <p role="alert" className="mt-4 text-sm text-red-600">{error}</p>}
      {summary && (
        <article className="mt-3 space-y-4">
          <h1 className="text-xl font-bold text-stone-900">{summary.title}</h1>
          <dl className="grid gap-x-6 gap-y-2 rounded-2xl bg-white p-4 text-sm shadow-sm ring-1 ring-stone-200 sm:grid-cols-[auto_1fr]">
            <dt className="text-stone-500">送信ユーザー</dt>
            <dd>
              {summary.user_name}（<a href={`mailto:${summary.user_email}`} className="underline">{summary.user_email}</a>）
            </dd>
            <dt className="text-stone-500">送信日時</dt>
            <dd>{formatDateTime(summary.submitted_at)}</dd>
            <dt className="text-stone-500">対応状況</dt>
            <dd>
              <select
                aria-label="対応状況"
                value={summary.handling_status}
                disabled={saving}
                onChange={(event) => changeStatus(event.target.value as HandlingStatus)}
                className="rounded-full border border-stone-300 bg-white px-3 py-1"
              >
                {Object.entries(HANDLING_STATUS_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </dd>
            {summary.mail_status === "failed" && (
              <>
                <dt className="text-red-600">メール</dt>
                <dd className="text-red-600">送信に失敗しました: {summary.mail_error}</dd>
              </>
            )}
          </dl>
          {/* 依頼者由来の内容のため、マークダウンはレンダーせずテキストのまま表示する */}
          <pre className="overflow-x-auto whitespace-pre-wrap break-words rounded-2xl bg-white p-4 text-sm leading-relaxed text-stone-800 shadow-sm ring-1 ring-stone-200">
            {summary.body_markdown}
          </pre>
        </article>
      )}
    </div>
  );
}

export default function AdminSummaryDetailPage() {
  return (
    <RequireAuth admin>
      <SummaryDetail />
    </RequireAuth>
  );
}
