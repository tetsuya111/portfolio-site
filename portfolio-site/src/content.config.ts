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

// 自動作成の IT 記事。スキーマは手で書いた記事と同じだが、別フォルダで管理し、/it-news/ に分けて表示する（/articles/・トップには出さない）
// （md は定期実行のビルドで作られ、S3 に保存される。git には .gitkeep だけを置く）
const itArticles = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/it-articles" }),
  schema: articleSchema,
});

// 自動作成のセキュリティ記事。IT 記事と同じく別フォルダで管理し、/security-news/ に分けて表示する（正本は S3。docs/security-articles.md）
const securityArticles = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/security-articles" }),
  schema: articleSchema,
});

export const collections = { profile, portfolios, articles, itArticles, securityArticles };
