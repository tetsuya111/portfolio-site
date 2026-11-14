# デザインテーマ

公開ページの見た目（色・書体・角丸）はテーマで切り替えられる。レイアウトの構造は全テーマで共通で、変わるのは見た目だけ。テーマはビルド時に1つに決まり、閲覧者がページ上で切り替えることはできない。

管理画面（`/admin/`）は `data-theme` を付けないのでテーマは切り替わらないが、同じ `global.css` を読むため、`:root` の値（既定テーマ）・本文の書体（`--font-sans`）・フォーカス枠は管理画面にも効く。`global.css` のこれらを変えるときは管理画面の見た目も確認する。

## テーマの一覧

| 名前 | 印象 |
|---|---|
| `minimal`（既定） | 落ち着いた・技術者らしい。インディゴのアクセント、等幅の小見出し、小さめの角丸 |
| `campus` | 明るい・親しみやすい。ブルーのアクセントとイエローのタグ、丸ゴシック系の見出し、大きめの角丸（参考: https://mycampus.jue.ac.jp/ の雰囲気） |

## テーマの選び方

次の順に、空でない最初の値を使う。どちらも空なら `minimal`。存在しない名前を指定するとビルドがエラーで止まる。

1. 環境変数 `PUBLIC_THEME`（例: `PUBLIC_THEME=campus npm run build`）。手元で別のテーマを試すときに使う。
2. [`src/site.config.ts`](../src/site.config.ts) の `theme`。公開するサイトのテーマはここで決める（コミットして push すればデプロイに反映される）。

AWS の CodeBuild（[infra/template.yaml](../infra/template.yaml)）には `PUBLIC_THEME` を渡す設定がない。コンソールで CodeBuild のプロジェクトに環境変数を足しても、スタックを更新すると消えるので、公開するサイトのテーマは `site.config.ts` で指定する。

テーマ名の決定は [`src/lib/theme.ts`](../src/lib/theme.ts) の `resolveTheme()`、`<html data-theme="...">` の出力は [`src/layouts/BaseLayout.astro`](../src/layouts/BaseLayout.astro)。

## 仕組み

[`src/styles/global.css`](../src/styles/global.css) に、テーマごとの変数 `--theme-*` を `[data-theme="<名前>"]` のブロックで定義している。`@theme inline` でこれを Tailwind のトークンにしているので、コンポーネントでは `text-fg`・`bg-accent` のように役割の名前で色を指定する。`text-slate-700` のような色の直接指定は使わない（`tests/no-hardcoded-colors.test.ts` で検出する）。

| 変数（`--theme-` の後） | 役割 | クラスの例 |
|---|---|---|
| `base` / `surface` | ページの背景 / カード・ヘッダーの背景 | `bg-page` `bg-surface`（`base` は文字サイズの `text-base` と重なるため `page` という名前にしている） |
| `fg` / `muted` | 本文の文字 / 補足（日付・肩書きなど）の文字 | `text-fg` `text-muted` |
| `line` | 罫線 | `border-line` `divide-line` |
| `accent` / `on-accent` | ボタンの塗り / その上の文字 | `bg-accent` `text-on-accent` |
| `accent-soft` / `on-accent-soft` | タグの背景 / その上の文字 | `bg-accent-soft` `text-on-accent-soft` |
| `link` | リンク・小見出しの文字 | `text-link` |
| `focus` | キーボードのフォーカス枠 | `ring-focus` |
| `hero-from` / `hero-to` | トップ・自己紹介の冒頭のグラデーション | `from-hero-from` `to-hero-to` |
| `font-body` / `font-heading` / `font-eyebrow` | 本文 / 見出し / 英大文字の小見出しの書体 | `font-sans` `font-heading` `font-eyebrow` |
| `radius` | カードの角丸 | `rounded-card` |

記事・自己紹介の本文（typography プラグイン）は `prose prose-themed`、塗りつぶしのボタン型リンクは `btn-accent`、英大文字の小見出しは `components/Eyebrow.astro` で同じ変数を使う。

ファビコン（`public/favicon.svg`）はテーマに関係なく同じ色にしている。

## テーマを追加する

1. `src/styles/global.css` に `[data-theme="<名前>"] { ... }` を追加し、上の変数をすべて定義する。色は `#rrggbb` 形式で書く。
2. `src/lib/theme.ts` の `THEMES` に名前を追加する。
3. `npm test` を実行する。`tests/theme-css.test.ts` が、全変数がそろっていることと、文字と背景のコントラスト比（文字 4.5:1 以上、フォーカス枠 3:1 以上）を全テーマについて検証する。
4. `PUBLIC_THEME=<名前> npm run build` してから `npm run preview` で見た目を確認する。

Web フォントは使わず OS 標準のフォントを並べて指定している（外部への読み込みを増やさないため）。
