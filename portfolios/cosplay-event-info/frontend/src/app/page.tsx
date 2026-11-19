"use client";

import Link from "next/link";

import { EventList } from "@/components/EventList";
import { fetchEvents } from "@/lib/api";
import { toIsoDate } from "@/lib/format";
import { useFetch } from "@/lib/useFetch";

const UPCOMING_COUNT = 5;

export default function HomePage() {
  const { data, error, loading } = useFetch(() => fetchEvents({ from: toIsoDate(new Date()) }), "upcoming");

  return (
    <>
      <section className="hero">
        <h1>コスプレイベント情報まとめ</h1>
        <p>
          複数のサイトに散らばっているコスプレイベントの予定とコスプレイヤーの情報を、1か所で検索できます。
          開催場所は地図で確認できます。
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          <Link className="button" href="/events/">
            イベントを探す
          </Link>
          <Link className="button" href="/map/">
            地図で見る
          </Link>
          <Link className="button" href="/cosplayers/">
            コスプレイヤーを探す
          </Link>
        </div>
      </section>
      <h2>これから開催されるイベント</h2>
      {error && <p className="error">{error}</p>}
      {loading && <p className="muted">読み込み中…</p>}
      {data && <EventList events={data.results.slice(0, UPCOMING_COUNT)} />}
      {data && data.count > UPCOMING_COUNT && (
        <p>
          <Link href={`/events/?from=${toIsoDate(new Date())}`}>すべて見る（{data.count} 件）</Link>
        </p>
      )}
    </>
  );
}
