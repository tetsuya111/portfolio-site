# 修正: S3 で正しく配信できないフロントエンドを登録しない

## 何を

- Next.js は `output: "export"` に加え `basePath: "/apps/<スラッグ>"`・`trailingSlash: true` がなければ登録しない（2周目で trailingSlash を追加）。
- SvelteKit・Nuxt・Remix などの Vite メタフレームワークと、サーバー出力の Astro も登録しない。
- `portfolio-site/docs/apps.md`・README・設計を更新。

## なぜ

- 登録すると、リソースやトップ以外のページが 404 になる、またはビルド成果物が見つからずデプロイ全体が止まるため（code-review 1・2周目の指摘）。
