"use client";

import { useEffect, useMemo, useRef } from "react";
import { Content, getMediaUrl, getPosterUrl } from "@/lib/api";

const MAX_ELEMENTS = 3;

interface VideoPoolProps {
  current: Content;
  /** 先読み対象。null なら先読みしない。 */
  next: Content | null;
  /** 戻る操作を速くするため metadata だけ保持しておく直前のコンテンツ。 */
  previous?: Content | null;
  muted: boolean;
  onEnded: () => void;
  /** 再生中の要素を外から操作するための参照。 */
  videoRef?: React.MutableRefObject<HTMLVideoElement | null>;
}

/**
 * 表示中・次・直前の動画要素をまとめて保持する。
 *
 * 単一の <video> の src を差し替えると、それまでに溜めたバッファが毎回破棄され、
 * スワイプのたびに接続からやり直しになる。要素を残したまま表示だけ切り替えることで、
 * 先読みしたバッファをそのまま再生に使える。
 */
export default function VideoPool({
  current,
  next,
  previous,
  muted,
  onEnded,
  videoRef,
}: VideoPoolProps) {
  const elementsRef = useRef<Map<string, HTMLVideoElement>>(new Map());

  // 保持する順序を固定する。id が同じなら React は要素を作り直さない。
  const entries = useMemo(() => {
    const seen = new Set<string>();
    const list: { content: Content; role: "current" | "next" | "previous" }[] = [];
    const push = (content: Content | null | undefined, role: "current" | "next" | "previous") => {
      if (!content || seen.has(content.id)) return;
      seen.add(content.id);
      list.push({ content, role });
    };
    push(current, "current");
    push(next, "next");
    push(previous, "previous");
    return list.slice(0, MAX_ELEMENTS);
  }, [current, next, previous]);

  // プールから外れた要素はバッファを明示的に解放する。
  useEffect(() => {
    const alive = new Set(entries.map((e) => e.content.id));
    for (const [id, el] of elementsRef.current) {
      if (alive.has(id)) continue;
      try {
        el.pause();
        el.removeAttribute("src");
        el.load();
      } catch {
        // 解放に失敗しても再生には影響しないため無視する。
      }
      elementsRef.current.delete(id);
    }
  }, [entries]);

  // 表示中のものだけ再生する。先読み中の要素は読み込むだけで再生しない。
  useEffect(() => {
    for (const { content, role } of entries) {
      const el = elementsRef.current.get(content.id);
      if (!el) continue;
      if (role === "current") {
        el.play().catch(() => {
          // 自動再生がブロックされた場合。ユーザー操作で再生される。
        });
      } else if (!el.paused) {
        el.pause();
      }
    }
  }, [entries]);

  return (
    <>
      {entries.map(({ content, role }) => {
        const isCurrent = role === "current";
        return (
          <video
            key={content.id}
            ref={(el) => {
              if (el) {
                elementsRef.current.set(content.id, el);
              } else {
                elementsRef.current.delete(content.id);
              }
              if (isCurrent && videoRef) videoRef.current = el;
            }}
            src={getMediaUrl(content)}
            poster={getPosterUrl(content)}
            // 先読み対象も auto にしないと先頭が取得されない。
            preload={role === "previous" ? "metadata" : "auto"}
            muted={isCurrent ? muted : true}
            playsInline
            onEnded={isCurrent ? onEnded : undefined}
            // 先読みの失敗は現在の再生を妨げない。
            onError={isCurrent ? undefined : () => {}}
            style={
              isCurrent
                ? {
                    width: "100%",
                    height: "100%",
                    objectFit: "contain",
                    display: "block",
                  }
                : {
                    position: "absolute",
                    width: 1,
                    height: 1,
                    opacity: 0,
                    pointerEvents: "none",
                    visibility: "hidden",
                  }
            }
          />
        );
      })}
    </>
  );
}
