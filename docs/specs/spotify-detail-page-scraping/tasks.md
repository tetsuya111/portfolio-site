# 詳細表示ページ解析 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `alltime.php` などの詳細表示ページから、`<script>` に埋め込まれた曲の行を直接取り出してプレイリストの元にできるようにする。

**Architecture:** `parser.py` に埋め込み文字列の取り出し（`extract_data_table_html`）・行の組み立て（`parse_detail_page`）・形式の振り分け（`parse_chart_page`）を追加し、`runner.py` の「その他のページ」経路だけを `parse_chart_page` に切り替える。

**Tech Stack:** Python 3.12、BeautifulSoup4、標準ライブラリ `re`、pytest、ruff

**Spec:** [requirements.md](requirements.md)・[design.md](design.md)

## Global Constraints

- コードの変更は `portfolios/spotify-billboard-playlist/` 配下のみ（作業ログはルートの `logs/`、既存設計の更新は `docs/specs/spotify-billboard-playlist/design.md`）。
- 取得先ホスト・HTTPS・リダイレクト非追従・タイムアウト 10 秒・応答上限 2 MB は変えない（N1）。`urls.py`・`fetcher.py` は変更しない。
- 新しい依存を追加しない（N2）。ページ内のスクリプトを実行しない（N3）。
- 失敗理由の文言: 詳細表示形式で0件のとき `詳細表示ページから曲を取り出せませんでした`。
- コマンドはすべて `portfolios/spotify-billboard-playlist/` で実行する（`npm run test:backend -- <pytest 引数>` は `backend/` を cwd にして pytest を起動する）。

## Review Focus

1. `$('#data-table')` 以外（例: `$('#other').append(…)`）に同じクラス名の行がある → 曲として拾わない（Task 1 `test_extract_ignores_other_targets`）。
2. 曲名に `’`・`\"`・`&amp;`・`<\/span>` が入る → 表示どおりの `’`・`"`・`&` になり、タグが壊れない（Task 1 `test_unescape_js_string`、Task 2 `test_parse_detail_page_rows`）。
3. 1曲だけ `span.artistLink` が欠ける → その行はアーティスト空文字で残り、他の行の対応はずれない（Task 2 `test_parse_detail_missing_artist_does_not_shift`）。
4. 同じ順位が2回出る → 後の行は最大順位+1 に繰り下げて残り、DB 保存で主キー違反にならない（Task 2 `test_parse_detail_duplicate_rank_moves_down`。実ページ確認により A4 を変更）。
5. 詳細表示形式だが中身が壊れていて0件 → 従来の「チャートの曲が見つかりませんでした」ではなく、詳細表示用の理由で失敗記録される（Task 3 `test_detail_page_without_rows_marked_failed`）。

---

### Task 1: 埋め込み文字列の取り出し（R2, R6, N3）

**Files:**
- Modify: `portfolios/spotify-billboard-playlist/backend/app/batch/parser.py`
- Create: `portfolios/spotify-billboard-playlist/backend/tests/fixtures/detail.html`
- Test: `portfolios/spotify-billboard-playlist/backend/tests/test_parser.py`

**Interfaces:**
- Produces: `extract_data_table_html(html: str) -> str | None`、`_unescape_js_string(body: str) -> str`

- [ ] **Step 1: フィクスチャを作る**（issue #3 に記載の構造から手作り。A3）

`tests/fixtures/detail.html` の内容（この文字列どおり。`’`・`\"`・`\'`・`<\/span>` はファイル上のバックスラッシュを含めた表記）:

```html
<html><body><table id="data-table"></table>
<script>
$(function(){
$('#data-table').append("<div class='row'><div class='number' style='display:none;'>2</div><span class='title' data-x=\"1\">Choosin’ Texas</span><span class='artistLink'><a href='/php/artist.php?a=1'>Ella Langley</a></span></div>");
$('#data-table').append("<div class='row'><div class='number' style='display:none;'>1</div>" + "<span class='title'>A Bar Song (Tipsy)</span><span class='artistLink'><a href='x'>Shaboozey</a></span></div>");
$("#data-table").append('<div class=\'number\'>3</div><span class="title">Rock &amp; Roll<\/span><span class="artistLink"><a>Simon</a> &amp; <a>Garfunkel</a></span>');
$('#other').append("<div class='number'>99</div><span class='title'>Decoy</span>");
});
</script></body></html>
```

- [ ] **Step 2: 失敗するテストを書く**（`test_parser.py` に追加）

```python
def test_unescape_js_string():
    assert _unescape_js_string(r"a\"b\'c\\d\/e’f\x41\n") == "a\"b'c\\d/e’fA\n"

def test_extract_data_table_html_joins_calls_in_order():
    fragment = extract_data_table_html(_read("detail.html"))
    assert fragment is not None
    assert fragment.index(">2</div>") < fragment.index(">1</div>") < fragment.index(">3</div>")
    assert "Choosin’ Texas" in fragment
    assert "</span>" in fragment and "\\" not in fragment

def test_extract_ignores_other_targets():
    assert "Decoy" not in extract_data_table_html(_read("detail.html"))

def test_extract_returns_none_without_append():
    assert extract_data_table_html(_read("hot100.html")) is None
```

- [ ] **Step 3: 失敗を確認**

Run: `npm run test:backend -- tests/test_parser.py -k "unescape or extract"`
Expected: FAIL（`ImportError: cannot import name 'extract_data_table_html'`）

- [ ] **Step 4: 実装する**

`parser.py` に [design.md](design.md) の「埋め込み文字列の取り出し」節の正規表現・手順どおりに2関数を追加する。対象テキストは `soup.find_all("script")` の各 `get_text()` を連結したもの。`codecs` の `unicode_escape` は使わない。

- [ ] **Step 5: 成功を確認**

Run: `npm run test:backend -- tests/test_parser.py`
Expected: PASS（既存テストも含めて全件）

- [ ] **Step 6: コミット**

```bash
git add backend/app/batch/parser.py backend/tests/fixtures/detail.html backend/tests/test_parser.py
git commit -m "feat(spotify): 詳細表示ページの埋め込み文字列を取り出す"
```

### Task 2: 行の組み立て（R2, R3, R5, A4, A5）

**Files:**
- Modify: `portfolios/spotify-billboard-playlist/backend/app/batch/parser.py`
- Test: `portfolios/spotify-billboard-playlist/backend/tests/test_parser.py`

**Interfaces:**
- Consumes: `extract_data_table_html`（Task 1）、既存の `ChartEntry`・`ParseError`・`_clean`、`parse_hot100`
- Produces: `parse_detail_page(html: str) -> list[ChartEntry]`、`parse_chart_page(html: str) -> list[ChartEntry]`

- [ ] **Step 1: 失敗するテストを書く**

```python
def test_parse_detail_page_rows():
    assert parse_detail_page(_read("detail.html")) == [
        ChartEntry(1, "A Bar Song (Tipsy)", "Shaboozey"),
        ChartEntry(2, "Choosin’ Texas", "Ella Langley"),
        ChartEntry(3, "Rock & Roll", "Simon & Garfunkel"),
    ]

def _detail(*rows: str) -> str:
    calls = "".join(f'$("#data-table").append("{r}");' for r in rows)
    return f"<script>{calls}</script>"

def test_parse_detail_missing_artist_does_not_shift():
    html = _detail(
        "<div class='number'>1</div><span class='title'>A</span>",
        "<div class='number'>2</div><span class='title'>B</span><span class='artistLink'>X</span>",
    )
    assert parse_detail_page(html) == [ChartEntry(1, "A", ""), ChartEntry(2, "B", "X")]

def test_parse_detail_duplicate_rank_keeps_first():
    html = _detail(
        "<div class='number'>1</div><span class='title'>First</span>",
        "<div class='number'>1</div><span class='title'>Second</span>",
    )
    assert parse_detail_page(html) == [ChartEntry(1, "First", "")]

def test_parse_detail_skips_bad_rank_and_empty_title():
    html = _detail(
        "<div class='number'>x</div><span class='title'>Bad</span>",
        "<div class='number'>2</div><span class='title'> </span>",
        "<div class='number'>3</div><span class='title'>Ok</span>",
    )
    assert parse_detail_page(html) == [ChartEntry(3, "Ok", "")]

def test_parse_detail_empty_raises():
    with pytest.raises(ParseError, match="詳細表示ページから曲を取り出せませんでした"):
        parse_detail_page(_detail("<p>no rows</p>"))

def test_parse_chart_page_dispatches():
    assert parse_chart_page(_read("detail.html"))[0].title == "A Bar Song (Tipsy)"
    assert parse_chart_page(_read("hot100.html")) == parse_hot100(_read("hot100.html"))
```

- [ ] **Step 2: 失敗を確認**

Run: `npm run test:backend -- tests/test_parser.py -k "detail or chart_page"`
Expected: FAIL（`ImportError: cannot import name 'parse_detail_page'`）

- [ ] **Step 3: 実装する**

[design.md](design.md) の「行の組み立て」「振り分け」節の手順1〜6どおりに `parse_detail_page`、続けて `parse_chart_page` を追加する。走査は `fragment_soup.find_all(True)` の文書順で、`"number" in tag.get("class", [])` かつ `tag.name == "div"` を行の区切りとする。

- [ ] **Step 4: 成功を確認**

Run: `npm run test:backend -- tests/test_parser.py`
Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add backend/app/batch/parser.py backend/tests/test_parser.py
git commit -m "feat(spotify): 詳細表示ページから順位・曲名・アーティストを取り出す"
```

### Task 3: バッチへの組み込み（R1, R4, R7）

**Files:**
- Modify: `portfolios/spotify-billboard-playlist/backend/app/batch/runner.py`（`process_source` の解析呼び出し）
- Test: `portfolios/spotify-billboard-playlist/backend/tests/test_runner.py`

**Interfaces:**
- Consumes: `parse_chart_page`（Task 2）

- [ ] **Step 1: 失敗するテストを書く**（`test_runner.py` に追加）

```python
ALLTIME_URL = "https://billboard.mryogaku.com/php/alltime.php?page=1"

def test_process_detail_page_directly(db):
    sid = db.add_source(ALLTIME_URL)
    fetcher = FakeFetcher({ALLTIME_URL: (FIXTURES / "detail.html").read_text(encoding="utf-8")})
    entries = process_source(db, sid, fetcher)
    assert [e.rank for e in entries] == [1, 2, 3]
    assert fetcher.calls == [ALLTIME_URL]
    assert db.get_source(sid)["status"] == "done"
    assert db.tracks(sid) == entries

def test_detail_page_without_rows_marked_failed(db):
    sid = db.add_source(ALLTIME_URL)
    fetcher = FakeFetcher({ALLTIME_URL: "<script>$('#data-table').append('<p>x</p>');</script>"})
    with pytest.raises(ParseError):
        process_source(db, sid, fetcher)
    source = db.get_source(sid)
    assert source["status"] == "failed"
    assert source["error"] == "詳細表示ページから曲を取り出せませんでした"
```

- [ ] **Step 2: 失敗を確認**

Run: `npm run test:backend -- tests/test_runner.py -k detail`
Expected: FAIL（`ParseError: チャートの曲が見つかりませんでした`）

- [ ] **Step 3: 実装する**

`process_source` で `target.kind == "page"` のとき `parse_chart_page(fetcher.get(url))`、それ以外は従来どおり `parse_hot100(fetcher.get(url))` にする。import を追加する。

- [ ] **Step 4: 回帰を含めて成功を確認**

Run: `npm run test:backend` と `npm run lint:backend`
Expected: すべて PASS、ruff の指摘 0 件（既存の `test_process_hot100_source`・`test_process_other_page_with_same_table`・`test_other_page_without_table_marked_failed` が通ることで R7 を確認）

- [ ] **Step 5: コミット**

```bash
git add backend/app/batch/runner.py backend/tests/test_runner.py
git commit -m "feat(spotify): 詳細表示ページをバッチで直接解析する"
```

### Task 4: ドキュメント更新と実ページ確認（R1〜R3、成功指標）

**Files:**
- Modify: `portfolios/spotify-billboard-playlist/README.md`（「受け付けるURL」節、現行 67〜71 行付近）
- Modify: `docs/specs/spotify-billboard-playlist/design.md`（「URL の検証・正規化」の表の「上記以外の同一ホストのパス」行と、その下の「ランキング系ページは…解析に失敗する」の文）
- Create: `logs/<yyyymmdd_hhMMss>_feat_spotify-detail-page-scraping.md`

- [ ] **Step 1: README に追記**: 「それ以外のページ」の項に、`alltime.php?page=N` など曲を `<script>` に埋め込んだ詳細表示ページは、そのページから直接（1ページ分、20曲）取り出す旨を1〜2行で書く。
- [ ] **Step 2: 既存設計を更新**: 上記2箇所を「詳細表示形式なら `parse_detail_page` で解析する。詳細は [docs/specs/spotify-detail-page-scraping/design.md](../spotify-detail-page-scraping/design.md)」に置き換える。
- [ ] **Step 3: 実ページで確認（外部アクセスのため、実行前に利用者の許可を得る）**

Run: `backend/.venv/Scripts/python -m app.batch --add "https://billboard.mryogaku.com/php/alltime.php?page=1"`（cwd は `backend/`）
Expected: `done` になり 20 曲。曲名・アーティストに `&amp;`・`\u`・`\"` が残っていない。許可が得られない場合は実施しなかった旨をログに書く。
- [ ] **Step 4: 作業ログを作成**（CLAUDE.md の規則どおり、何を・なぜ）
- [ ] **Step 5: コミット**

```bash
git add README.md ../../docs/specs/spotify-billboard-playlist/design.md ../../logs/
git commit -m "docs(spotify): 詳細表示ページの解析に対応した旨を追記"
```

## 要件との対応

| 要件 | タスク |
|---|---|
| R1 | Task 3（`test_process_detail_page_directly`）、Task 4 Step 3 |
| R2 | Task 1、Task 2 |
| R3 | Task 2（`test_parse_detail_page_rows`）、Task 4 Step 3 |
| R4 | Task 2（`test_parse_detail_empty_raises`）、Task 3（`test_detail_page_without_rows_marked_failed`） |
| R5 | Task 2（`test_parse_detail_page_rows` の `&amp;`） |
| R6 | Task 1（`test_unescape_js_string`）、Task 2（`’`） |
| R7 | Task 2（`test_parse_chart_page_dispatches`）、Task 3 Step 4 の既存テスト |
| N1〜N3 | Global Constraints（`urls.py`・`fetcher.py` 不変、依存追加なし、正規表現のみ） |
