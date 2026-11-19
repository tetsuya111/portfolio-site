import { formatDate } from "@/lib/format";
import type { CosplayerDetail } from "@/lib/types";
import { safeHttpUrl, snsLabel } from "@/lib/url";

import { ExternalLink } from "./ExternalLink";

/** コスプレイヤーの詳細なプロフィール（CP-5）。文字列はすべてテキストとして表示する。 */
export function CosplayerProfile({ cosplayer }: { cosplayer: CosplayerDetail }) {
  const sns = cosplayer.sns_links.filter((u) => safeHttpUrl(u));
  return (
    <article>
      <h1>{cosplayer.name}</h1>
      <dl className="detail-table card">
        <dt>SNS</dt>
        <dd>
          {sns.length === 0 ? (
            "なし"
          ) : (
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              {sns.map((url) => (
                <li key={url}>
                  <ExternalLink href={url}>{snsLabel(url)}</ExternalLink>
                </li>
              ))}
            </ul>
          )}
        </dd>
        <dt>説明文</dt>
        <dd>{cosplayer.description || "なし"}</dd>
        <dt>経歴</dt>
        <dd>{cosplayer.career || "なし"}</dd>
        <dt>備考</dt>
        <dd>{cosplayer.notes || "なし"}</dd>
      </dl>
      <h2>取得元</h2>
      <ul>
        {cosplayer.sources.map((s) => (
          <li key={s.url}>
            <ExternalLink href={s.url} />{" "}
            <span className="muted">（{formatDate(s.fetched_at.slice(0, 10))} 取得）</span>
          </li>
        ))}
        {cosplayer.sources.length === 0 && cosplayer.source_url && (
          <li>
            <ExternalLink href={cosplayer.source_url} />
          </li>
        )}
      </ul>
    </article>
  );
}
