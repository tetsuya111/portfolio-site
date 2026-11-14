# 設計: 詳細表示ページ（alltime.php 等）から曲名を直接取り出す

要件: [requirements.md](requirements.md)　既存設計: [docs/specs/spotify-billboard-playlist/design.md](../spotify-billboard-playlist/design.md)

## TL;DR

`parser.py` に、`<script>` 内の `$('#data-table').append(…)` の文字列リテラルを正規表現で取り出し、JavaScript のエスケープを戻してから BeautifulSoup で読む `parse_detail_page` を追加する。`runner.py` は「その他のページ」（`ChartTarget.kind == "page"`）を解析するとき、詳細表示形式なら新しい解析、そうでなければ従来の表の解析を使う。URL の正規化・取得・DB・API・フロントエンドは変えない。

## Non-Goals（技術面）

- requirements.md の Non-Goals を引き継ぐ（複数ページの結合、取得制約の緩和、`chart.php` 置き換えの廃止、JS 実行）。
- JavaScript の完全な字句解析はしない。対象は「`$('#data-table').append(` の直後に並ぶ文字列リテラル（`+` 連結を含む）」に限る。テンプレートリテラル（`` ` ``）・変数の連結・関数呼び出しを含む引数は対象外で、そうした行は取り出さない。

## 処理の流れ（R1・R7）

```
process_source
  └ resolve_chart_url(url)            … 変更なし（alltime.php は kind="page"）
  └ fetcher.get(target.url)           … 変更なし（N1）
  └ kind == "page"  → parse_chart_page(html)   ← 新規（R1）
      ├ extract_data_table_html(html) が None 以外 → parse_detail_page(html)
      └ None                                       → parse_hot100(html)（従来どおり、R7）
    kind in {"hot100","top"} → parse_hot100(html)  … 変更なし（R7・A2）
```

`hot100`/`top` の経路は変えない。`chart.php` は従来どおり `dispHot100.php` に置き換わるため、新しい解析は通らない（A2）。

## 解析（`parser.py`）

### 埋め込み文字列の取り出し（R2・R6・N3）

`extract_data_table_html(html: str) -> str | None`

1. ページ全体の文字列に対して、次の正規表現で `append` 呼び出しの引数部分を探す（`<script>` の中身だけを対象にするため、BeautifulSoup で `script` 要素のテキストを連結したものに対して適用する）。
   - 呼び出し: `\$\(\s*(['"])#data-table\1\s*\)\s*\.append\(\s*(引数)\s*\)`
   - 引数: 文字列リテラルを `+` でつないだ並び。文字列リテラルは `"(?:[^"\\\n]|\\.)*"` または `'(?:[^'\\\n]|\\.)*'`。
2. 引数中の各リテラルの中身を `_unescape_js_string` で戻し、出現順に連結する。全呼び出し分をさらに出現順に連結して返す。
3. 呼び出しが1つもなければ `None`（＝詳細表示形式ではない）。

`_unescape_js_string(body: str) -> str` は `\\(u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|.)` を1回の `re.sub` で置き換える。`n`/`t`/`r` は改行・タブ・復帰、`uXXXX`/`xXX` はその文字、それ以外（`"` `'` `\` `/` など）は直後の文字そのものにする。

### 行の組み立て（R2・R3・R5）

`parse_detail_page(html: str) -> list[ChartEntry]`

1. `extract_data_table_html` の結果を `BeautifulSoup(fragment, "html.parser")` で読む。HTML エンティティ（`&amp;`・`&rsquo;` など）はこの時点で文字に戻る（R5）。
2. 断片内の `div.number` ごとに1行を組む。`div.number` から親をたどり、その `div.number` だけを含む最も外側の要素（実ページでは曲ごとの `<tr>`）を行とみなし、その中の最初の `span.title` を曲名、最初の `span.artistLink` をアーティスト名とする（行内の並び順は問わない。行内に曲名が無ければその行は捨て、他の行の曲名は借りない）。複数行が同じ親に平たく並ぶ場合は、次の `div.number` までに現れた最初の `span.title`・`span.artistLink` を使う。
   - 2026-11-14 に実ページで確認した構造: 1曲ごとに `<tr>` の中の `td.rborder` に、`span.title` → 非表示の `div.number` → `span.artistLink` の順で並ぶ（曲名が `div.number` より前）。当初の「`div.number` から次の `div.number` まで」の規則だけでは、曲名が1行ずつずれるため上記に改めた。
3. テキストは既存の `_clean`（空白正規化）を通す。アーティストは `span.artistLink` の `get_text()`（中の `<a>` が複数でも連結される）。
4. 採用条件: 順位が整数に変換でき（1〜100000 の範囲外は捨てる）、曲名が空でない。アーティストが無い行は空文字で採用する（A5）。同じ順位が再び現れたら、後の行は捨てずに残す（手順5で繰り下げる。A4）。
5. 順位で安定ソートし、直前の行以下の順位になった行は直前の順位+1 に繰り下げて返す（R3・A4）。
6. 1件も採用できなければ `ParseError("詳細表示ページから曲を取り出せませんでした")`（R4）。

### 振り分け（R1・R7）

`parse_chart_page(html: str) -> list[ChartEntry]`: `extract_data_table_html(html)` が `None` でなければ取り出した断片を詳細表示として解析し、`None` なら `parse_hot100` を呼ぶ。詳細表示の解析で0件だった場合は `parse_hot100` も試し、両方0件なら詳細表示の理由（R4）で失敗する（表形式のページにたまたま `#data-table` への `append` があっても従来どおり読めるようにするため）。形式の判定はページ名ではなく中身で行う（A1）。

## 実行（`runner.py`、R1・R4）

`process_source` の解析呼び出しを、`target.kind == "page"` のとき `parse_chart_page`、それ以外は従来の `parse_hot100` にする。`ParseError` は既存の `BatchError` に含まれているため、失敗の記録（`mark_failed`）は追加実装なしで R4 を満たす。

## ドキュメントの更新

- [portfolios/spotify-billboard-playlist/README.md](../../../portfolios/spotify-billboard-playlist/README.md) の「受け付けるURL」節に、詳細表示ページ（`alltime.php?page=N` など）を直接解析できることを追記する。
- 既存設計 [docs/specs/spotify-billboard-playlist/design.md](../spotify-billboard-playlist/design.md) の「その他の同一ホストのページ」行と、「ランキング系ページは解析に失敗する」の記述を、この設計へのリンク付きで更新する（単一情報源の原則に従い、詳細はこの design.md に置く）。

## 検討した代替案

- **ページ名（`alltime.php` など）で判定する**: 判定は単純になるが、同じ形式のページ（`no1weeks.php` など）を追加するたびに改修が要る。中身での判定を採用。
- **`codecs.decode(s, "unicode_escape")` でエスケープを戻す**: 非 ASCII 文字（`’` や日本語）が Latin-1 として壊れるため不採用。
- **スクリプト内の文字列リテラルをすべて連結して読む**: 実装は短いが、`#data-table` 以外への `append` やその他の文字列（例: 別の表）まで曲として拾う恐れがある。`$('#data-table').append(` の引数に限定する案を採用。
- **JavaScript を実行して描画後の DOM を読む（Playwright・js2py など）**: 構造の変化に強いが、新しい依存と、取得したページのスクリプトを実行する攻撃面が増える（N2・N3 に反する）。不採用。
- **`div.number`・`span.title`・`span.artistLink` をそれぞれ集めて順番で対応付ける**: 1曲だけアーティストが欠けると以降の対応がすべてずれる。`div.number` を区切りにして行を組む案を採用。
- **`chart.php` も詳細解析に切り替える**: 40曲に減るため不採用（A2）。

## 横断的関心事

- **セキュリティ・プライバシー**: 取得先・取得制約は変えない（N1）。取得したスクリプトは実行せず、正規表現で文字列として読むだけ（N3）。正規表現は入れ子の量指定を持たない線形の形にし、応答は既存の 2 MB 上限で打ち切られるため、極端に重い入力にはならない。取り出した文字列は BeautifulSoup でテキストとして扱い、HTML のまま保存・表示しない。
- **パフォーマンス・スケーラビリティ**: 1ページ20曲・数十KB 程度で、既存の表解析と同程度。影響なし。
- **オブザーバビリティ**: 既存の `runner` のログ（成功時の曲数、失敗時の理由）で足りる。失敗理由の文言で「詳細表示ページだったが取れなかった」と「表も詳細形式も無かった」を区別できる（R4）。
- **テスト戦略**: 手作りのフィクスチャ `tests/fixtures/detail.html`（A3）で `parser` の単体テストを書き、`runner` のテストで「その他のページ」経路の結合を確認する。既存テストが通ること（R7 の回帰確認）を合わせて見る。実ページでの確認は、実装時に利用者の許可を得てから `python -m app.batch --add` で行う。
- **ロールアウト計画**: ローカル実行のみのアプリで、DB スキーマも変えないためマイグレーション不要。戻す場合は該当コミットを revert するだけでよい。

## 既存アーキテクチャとの整合性

- 既存の `parser.py` / `runner.py` の分担（解析は `parser`、流れと失敗記録は `runner`）に従う。
- `ChartEntry`・`ParseError`・`_clean` を再利用し、新しい型や例外は増やさない。
- 既存設計の「その他のページは Hot 100 と同じセレクターで解析する」から、「詳細表示形式ならそちらで解析する」に広げる。これは意図した変更で、上記「ドキュメントの更新」で既存設計に反映する。
