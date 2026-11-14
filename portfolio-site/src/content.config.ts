import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";
import { articleSchema, portfolioSchema, profileSchema } from "./lib/schemas";

// md ファイルの frontmatter をコレクションのデータ（「DB」）として扱う
const profile = defineCollection({
  loader: glob({ pattern: "profile.md", base: "./src/content/profile" }),
  schema: profileSchema,
});

const portfolios = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/portfolios" }),
  schema: portfolioSchema,
});

const articles = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/articles" }),
  schema: articleSchema,
});

// 自動作成の IT 記事。手で書いた記事と別フォルダで管理するが、スキーマは同じで同じ一覧・記事ページに出す
// （md は定期実行のビルドで作られ、S3 に保存される。git には .gitkeep だけを置く）
const itArticles = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/it-articles" }),
  schema: articleSchema,
});

export const collections = { profile, portfolios, articles, itArticles };
