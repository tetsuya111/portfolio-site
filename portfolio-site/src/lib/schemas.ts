// frontmatter のスキーマ。content.config.ts（ビルド時）と content-store.ts（保存時）で共用し、
// 両者の判定がずれないようにする。
import { z } from "astro/zod";

/** http/https の URL だけを受け付ける（javascript: などをリンクにしないため）。 */
const httpUrl = z.url({ protocol: /^https?$/ });

export const profileSchema = z.object({
  name: z.string().min(1),
  role: z.string().min(1),
  summary: z.string().optional(),
  links: z.array(z.object({ label: z.string().min(1), url: httpUrl })).optional(),
});

export const portfolioSchema = z.object({
  title: z.string().min(1),
  tags: z.array(z.string().min(1)).default([]),
  url: httpUrl.optional(),
  date: z.coerce.date().optional(),
});

export const articleSchema = z.object({
  title: z.string().min(1),
  date: z.coerce.date(),
  tags: z.array(z.string().min(1)).default([]),
  description: z.string().optional(),
  draft: z.boolean().default(false),
});

export type Profile = z.infer<typeof profileSchema>;
export type Portfolio = z.infer<typeof portfolioSchema>;
export type Article = z.infer<typeof articleSchema>;

/** zod の検証エラーを「項目: 理由」の文字列配列にする（API・コマンドの表示用）。 */
export function formatIssues(error: z.ZodError): string[] {
  return error.issues.map((i) => `${i.path.join(".") || "(全体)"}: ${i.message}`);
}
