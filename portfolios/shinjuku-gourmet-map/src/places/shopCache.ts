import type { ShopSearcher } from "./searchShops";
import type { Shop } from "./shop";

/**
 * ジャンル単位で検索結果をメモリに保持する（ページを開いている間だけ）。
 * 同じジャンルを選び直しても Google へ再検索しないため、無料利用枠を節約できる。
 * 失敗した検索は保持しないので、押し直せば再検索する。
 */
export function cacheByGenre(search: ShopSearcher): ShopSearcher {
  const cache = new Map<string, Promise<Shop[]>>();
  return (genre) => {
    const hit = cache.get(genre.id);
    if (hit) return hit;
    const pending = search(genre);
    cache.set(genre.id, pending);
    pending.catch(() => cache.delete(genre.id));
    return pending;
  };
}
