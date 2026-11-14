"use client";

import { type FormEvent, useState } from "react";
import * as api from "@/lib/api";

const DEFAULT_URL = "https://billboard.mryogaku.com/";
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
/**
 * プレイリスト名は `{タイトル}-yyyy/mm/dd` に統一する。タイトルはチャートページの <title>
 * （サイト名を除く）を使い、取れなかったときはこの既定のタイトルにする。
 */
const DEFAULT_PLAYLIST_TITLE = "ビルボード Hot 100";
/** タイトル内の日付表記（2025年11月15日付・2025/11/15・2025-11-15 など）。括弧で囲まれていれば括弧ごと。 */
const DATE_NOTATION = String.raw`\d{4}\s*(?:年\s*\d{1,2}\s*月\s*\d{1,2}\s*日|[/.-]\d{1,2}[/.-]\d{1,2})\s*付?`;
const TITLE_DATE_RE = new RegExp(String.raw`[（(]\s*${DATE_NOTATION}\s*[）)]|${DATE_NOTATION}`, "g");
/** プレイリスト名の最大文字数（バックエンドの検証と同じ値）。 */
const MAX_NAME_LENGTH = 100;
/** POST /api/playlists が1回で受け付ける曲数の上限（バックエンドの検証と同じ値）。 */
const MAX_TRACKS = 100;

type Props = { authenticated: boolean; onUnauthorized?: () => void };

function formatDate(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}/${pad(d.getMonth() + 1)}/${pad(d.getDate())}`;
}

/**
 * ページのタイトルと、URL の date パラメータ（なければ今日の日付）からプレイリスト名を作る。
 * 日付は末尾に付けるため、タイトル内の日付表記は除く。
 */
export function playlistName(url: string, pageTitle: string | undefined, today: Date = new Date()): string {
  let date: string | null = null;
  try {
    date = new URL(url).searchParams.get("date");
  } catch {
    date = null;
  }
  const yyyymmdd = date && DATE_RE.test(date) ? date.replaceAll("-", "/") : formatDate(today);
  const suffix = `-${yyyymmdd}`;
  // 文字数はコードポイント単位で数える（バックエンドの検証と同じ数え方）
  // title を返さない古いバックエンドでも動くよう、無ければ空文字として扱う
  const pageName = (pageTitle ?? "").replace(TITLE_DATE_RE, " ").replace(/\s+/g, " ").trim();
  const title = Array.from(pageName || DEFAULT_PLAYLIST_TITLE)
    .slice(0, MAX_NAME_LENGTH - suffix.length)
    .join("")
    .trim();
  return `${title}${suffix}`;
}

export default function PlaylistForm({ authenticated, onUnauthorized }: Props) {
  const [url, setUrl] = useState(DEFAULT_URL);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<api.PlaylistResult | null>(null);
  // 取得した曲数が上限を超えて先頭だけを送ったときの元の曲数
  const [truncatedFrom, setTruncatedFrom] = useState<number | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = url.trim();
    if (!trimmed || loading) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setTruncatedFrom(null);
    try {
      const chart = await api.fetchChart(trimmed);
      const tracks = chart.tracks.slice(0, MAX_TRACKS).map(({ title, artist }) => ({ title, artist }));
      if (chart.tracks.length > MAX_TRACKS) setTruncatedFrom(chart.tracks.length);
      setResult(await api.createPlaylist(playlistName(trimmed, chart.title), tracks));
    } catch (e) {
      // バックエンド由来でない例外は原因が画面に出ないため、調査用にコンソールへ残す
      if (!(e instanceof api.ApiError)) console.error(e);
      const err = e instanceof api.ApiError ? e : new api.ApiError(0, "予期しないエラーが発生しました");
      setError(err.message);
      if (err.status === 401) onUnauthorized?.();
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card">
      <form onSubmit={handleSubmit}>
        <label htmlFor="chart-url">チャートURL</label>
        <input
          id="chart-url"
          type="url"
          required
          maxLength={2048}
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder={DEFAULT_URL}
        />
        <button type="submit" className="button primary" disabled={!authenticated || loading}>
          {loading ? "作成中…" : "プレイリストを作成"}
        </button>
        {!authenticated && <p className="hint">プレイリストを作成するには Spotify にログインしてください。</p>}
      </form>

      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}

      {result && (
        <div className="result">
          <p>
            作成しました:{" "}
            <a href={result.url} target="_blank" rel="noopener noreferrer">
              Spotifyで開く
            </a>
          </p>
          <p>追加した曲: {result.added}曲</p>
          {truncatedFrom !== null && (
            <p className="hint">
              ページには{truncatedFrom}曲ありましたが、先頭の{MAX_TRACKS}曲だけを対象にしました。
            </p>
          )}
          {result.not_found.length > 0 && (
            <>
              <p>見つからなかった曲（{result.not_found.length}曲）:</p>
              <ul>
                {result.not_found.map((t, i) => (
                  <li key={`${i}-${t.title}`}>
                    {t.title} / {t.artist}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </section>
  );
}
