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

export const collections = { profile, portfolios, articles };
