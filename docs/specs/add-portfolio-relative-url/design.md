# 設計: 取り込んだフロントエンドの URL をサイト内の相対パスで保存する

要件: [requirements.md](requirements.md)

## TL;DR

importer は配信登録時の `url` を既定で `/apps/<スラッグ>/` にする（`--site-url` 指定時のみ絶対 URL）。サイトの `portfolioSchema.url` は「http(s) の URL」または「安全なサイト内パス」を受け付ける。表示側のコードは `href={url}` のままで変更不要。

## 全体構成と変更点

| ファイル | 変更 | 要件 |
|---|---|---|
| `portfolios/portfolio-importer/importer/cli.py` | `app_url` を `site_url` 有無で絶対／相対に分ける | R1-1, R1-2 |
| `portfolios/portfolio-importer/importer/content.py` | http(s) 検証をメタデータ由来の `url` だけに適用し、`app_url` はそのまま使う | R1-3 |
| `portfolio-site/src/lib/schemas.ts` | `portfolioUrl = httpUrl.or(sitePath)` を追加し `portfolioSchema.url` に使う | R2-1, R2-2 |
| `portfolio-site/src/components/PortfolioTile.astro`・`pages/portfolios/[slug].astro` | 変更なし（`href={url}` がパスでもそのまま動く） | R2-3 |
| `.claude/skills/add-portfolio/SKILL.md`・importer `README.md` | `--site-url` の説明更新、ドメイン探索手順の削除 | R3-1 |

## 各部の設計

### importer（R1-1〜R1-3）

```python
if registered:
    app_url = f"{args.site_url.rstrip('/')}/apps/{slug}/" if args.site_url else f"/apps/{slug}/"
else:
    app_url = None
```

`write_portfolio_md` は `app_url` が与えられればそれを採用し、なければメタデータの `url` を `_HTTP` で検証して採用する。`app_url` はコード内で組み立てた値（スラッグは `resolve_target` で検証済み）のため再検証しない。

### スキーマ（R2-1, R2-2）

```ts
/** サイト内のパス。//host・/\host（別ホストになる）と空白・制御文字・\ を拒否する。 */
const sitePath = z.string().regex(/^\/(?![/\])[^\s\]*$/u);
const portfolioUrl = z.union([httpUrl, sitePath]);
```

`\s` は JS では Unicode 空白を含む。制御文字（`\x00-\x1f`, `\x7f`）も明示的に除外する: `/^\/(?![/\])[^\s\\x00-\x1f\x7f]*$/`。

## テスト方針

- importer: `test_cli.py` に「`--site-url` なしで相対パス」「未登録なら url なし（メタデータの http URL のみ）」、`test_content.py` に「`app_url` の相対パスを保存」「メタデータの相対パスは捨てる」を追加。
- サイト: `schemas.test.ts` に `/apps/x/` を受理、`//evil.com`・`/\evil.com`・`/a b`・`/a\b`・`javascript:` を拒否、`profileSchema.links` の相対パスを拒否するケースを追加。

## 検討した代替案

- `--site-url` を廃止する: 絶対 URL で保存したい運用を失うため不採用（A1）。
- 表示時にドメインを付け替える（ビルド時の環境変数）: issue の Non-Goals。
- 相対パスなら `target="_blank"` を外す: 表示の挙動が変わる割に利点が小さいため不採用（A6）。

## リスク

- 相対パスのリンクはローカルの `astro dev` では `/apps/` が配信されないと 404 になる。本番・dev の配信では CloudFront が `/apps/` を返すため問題ない。
