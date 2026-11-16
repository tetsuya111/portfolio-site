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
  /** 表示を始める。initial を省略すると先頭のジャンルを選ぶ */
  start(initial?: Genre): Promise<void>;
  selectGenre(genre: Genre): Promise<void>;
  /** 閲覧者が詳細パネルを閉じたときに呼ぶ */
  handleDetailClosed(): void;
  /** 地図が使えなくなったとき（APIキーの認証失敗など）に、以降の操作と表示更新を止める */
  disable(): void;
}

const loadErrorMessage = (genre: Genre) =>
  `${genre.label}のお店を読み込めませんでした。時間をおいてもう一度お試しください。`;

/** ジャンル選択 → 検索 → ピン表示 → 詳細表示の流れを管理する */
export function createApp(deps: AppDependencies): App {
  const { search, layer, status, detail, setActiveGenre } = deps;
  /** 最後に押されたジャンルの検索だけを反映するための通し番号 */
  let latestRequest = 0;
  let disabled = false;

  const selectShop = (shop: Shop) => {
    layer.highlight(shop.id);
    detail.show(shop);
  };

  const selectGenre = async (genre: Genre) => {
    if (disabled) return;
    const request = ++latestRequest;
    const isStale = () => request !== latestRequest;
    // 先にピンを消す（詳細を閉じるときに、消えるピンへフォーカスを戻さないため）
    layer.clear();
    detail.hide();
    setActiveGenre(genre.id);
    status.loading(genre);

    try {
      const shops = await search(genre);
      if (isStale()) return;
      layer.show(shops, selectShop);
      status.result(genre, shops.length);
    } catch (error) {
      if (isStale()) return;
      console.error(`「${genre.query}」の表示に失敗しました`, error);
      layer.clear(); // 途中まで描かれたピンを残さない
      status.error(loadErrorMessage(genre));
    }
  };

  return {
    async start(initial) {
      const genre = initial ?? deps.genres[0];
      if (genre) await selectGenre(genre);
    },
    selectGenre,
    handleDetailClosed() {
      layer.highlight(null);
    },
    disable() {
      disabled = true;
      latestRequest++; // 検索中の結果を捨てる
      layer.clear();
      detail.hide();
    },
  };
}
