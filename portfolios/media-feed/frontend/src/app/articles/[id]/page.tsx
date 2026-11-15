import { Suspense } from "react";
import ArticlePageClient from "@/components/ArticlePageClient";

// 静的出力（output: "export"）では動的ルートのページを事前に作る必要がある。
// ポートフォリオのモック（handlers.js）が返すデモ用の値だけを出力する。
export function generateStaticParams() { return [{ id: "1" }]; }

export default async function ArticlePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <Suspense>
      <ArticlePageClient id={id} />
    </Suspense>
  );
}
