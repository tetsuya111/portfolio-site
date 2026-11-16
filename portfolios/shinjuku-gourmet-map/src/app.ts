import type { Genre } from "./config/parseMapConfig";
import type { MarkerLayer } from "./maps/markerLayer";
import type { ShopSearcher } from "./places/searchShops";
import type { Shop } from "./places/shop";
import type { ShopDetail } from "./ui/shopDetail";
import type { StatusView } from "./ui/statusView";

export interface AppDependencies {
  genres: Genre[];
  search: ShopSearcher;
  layer: MarkerLayer;
  status: StatusView;
  detail: ShopDetail;
  /** ジャンルボタンの選択状態を切り替える */
  setActiveGenre: (genreId: string) => void;
}

export interface App {
  /** 先頭のジャンルを選んで表示を始める */
  start(): Promise<void>;
  selectGenre(genre: Genre): Promise<void>;
  /** 閲覧者が詳細パネルを閉じたときに呼ぶ */
  handleDetailClosed(): void;
}

/** ジャンル選択 → 検索 → ピン表示 → 詳細表示の流れを管理する */
export function createApp(deps: AppDependencies): App {
  const { search, layer, status, detail, setActiveGenre } = deps;
  /** 最後に押されたジャンルの検索だけを反映するための通し番号 */
  let latestRequest = 0;

  const selectShop = (shop: Shop) => {
    layer.highlight(shop.id);
    detail.show(shop);
  };

  const selectGenre = async (genre: Genre) => {
    const request = ++latestRequest;
    detail.hide();
    layer.clear();
    setActiveGenre(genre.id);
    status.loading(genre);

    let shops: Shop[];
    try {
      shops = await search(genre);
    } catch (error) {
      if (request !== latestRequest) return;
      console.error(`「${genre.query}」の検索に失敗しました`, error);
      status.error(`${genre.label}のお店を読み込めませんでした。時間をおいてもう一度お試しください。`);
      return;
    }
    if (request !== latestRequest) return;

    layer.show(shops, selectShop);
    status.result(genre, shops.length);
  };

  return {
    async start() {
      const [first] = deps.genres;
      if (first) await selectGenre(first);
    },
    selectGenre,
    handleDetailClosed() {
      layer.highlight(null);
    },
  };
}
