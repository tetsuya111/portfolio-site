# コンテンツ: spotify-billboard-playlist をポートフォリオに追加

## 何を

- `/add-portfolio` の手順で `portfolios/spotify-billboard-playlist` を取り込んだ（`portfolios/` 配下のためコピーなし）。
- `backend/Dockerfile`・`backend/.dockerignore` を生成し、`portfolio-site/src/content/portfolios/spotify-billboard-playlist.md` を作成した。サイト上で開けない相対リンクは文章に置き換えた。
- フロントエンドは Next.js に `output: "export"` がなく静的出力できないため、配信登録していない。Docker イメージは外部取得を伴うため作成していない。

## なぜ

- 新しいスキル・コマンドの動作を既存のプロジェクトで確認し、その成果をサイトに掲載するため。
