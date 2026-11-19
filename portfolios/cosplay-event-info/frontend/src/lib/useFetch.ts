"use client";

import { useEffect, useState } from "react";

import { ApiError } from "./api";

type Result<T> = { key: string; data: T | null; error: string | null };

/**
 * key が変わるたびに load を呼び、結果・エラー・読み込み中を返す。
 * 読み込み中かどうかは「手元の結果が今の key のものか」で判断し、古い応答は捨てる。
 */
export function useFetch<T>(load: (() => Promise<T>) | null, key: string) {
  const [result, setResult] = useState<Result<T> | null>(null);

  useEffect(() => {
    if (!load) return;
    let active = true;
    load()
      .then((data) => {
        if (active) setResult({ key, data, error: null });
      })
      .catch((e: unknown) => {
        const message = e instanceof ApiError ? e.message : "読み込みに失敗しました。";
        if (active) setResult({ key, data: null, error: message });
      });
    return () => {
      active = false;
    };
    // load は毎回作り直される関数のため、依存は key だけにする
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const current = result?.key === key ? result : null;
  return {
    data: current?.data ?? null,
    error: current?.error ?? null,
    loading: load !== null && current === null,
  };
}
