"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { CosplayerProfile } from "@/components/CosplayerProfile";
import { fetchCosplayer } from "@/lib/api";
import { useFetch } from "@/lib/useFetch";

function CosplayerDetailContent() {
  const id = Number(useSearchParams().get("id"));
  const valid = Number.isInteger(id) && id > 0;
  const { data, error, loading } = useFetch(valid ? () => fetchCosplayer(id) : null, String(id));

  if (!valid) return <p className="error">コスプレイヤーが指定されていません。</p>;
  if (loading) return <p className="muted">読み込み中…</p>;
  if (error || !data) return <p className="error">{error ?? "コスプレイヤーが見つかりません。"}</p>;
  return (
    <>
      <p>
        <Link href="/cosplayers/">← コスプレイヤー一覧へ</Link>
      </p>
      <CosplayerProfile cosplayer={data} />
    </>
  );
}

export default function CosplayerDetailPage() {
  return (
    <Suspense fallback={<p className="muted">読み込み中…</p>}>
      <CosplayerDetailContent />
    </Suspense>
  );
}
