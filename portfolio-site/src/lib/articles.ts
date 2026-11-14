// 記事の取得（Astro のコンテンツコレクションに依存する部分）。
// 手で書いた記事（src/content/articles）と自動作成の記事（src/content/it-articles）を同じように表示する。
import { getCollection } from "astro:content";
import { mergeArticleEntries } from "./content-query";

/** 自動作成の記事（IT ニュース）だけ。 */
export function getItArticles() {
  return getCollection("itArticles");
}

/** 手で書いた記事と自動作成の記事をまとめたもの（並び替え・下書きの除外は publishedArticles で行う）。 */
export async function getAllArticles() {
  return mergeArticleEntries(await getCollection("articles"), await getItArticles());
}
