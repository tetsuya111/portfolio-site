"use client";

import { type FormEvent, useState } from "react";
import * as api from "@/lib/api";

const DEFAULT_URL = "https://billboard.mryogaku.com/";
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

type Props = { authenticated: boolean; onUnauthorized?: () => void };

function formatDate(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** URL の date パラメータ（なければ今日の日付）からプレイリスト名を作る。 */
export function playlistName(url: string, today: Date = new Date()): string {
  let date: string | null = null;
  try {
    date = new URL(url).searchParams.get("date");
  } catch {
    date = null;
  }
  return `Billboard Hot 100 (${date && DATE_RE.test(date) ? date : formatDate(today)})`;
}

export default function PlaylistForm({ authenticated, onUnauthorized }: Props) {
  const [url, setUrl] = useState(DEFAULT_URL);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<api.PlaylistResult | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = url.trim();
    if (!trimmed || loading) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const chart = await api.fetchChart(trimmed);
      const tracks = chart.tracks.map(({ title, artist }) => ({ title, artist }));
      setResult(await api.createPlaylist(playlistName(trimmed), tracks));
    } catch (e) {
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
