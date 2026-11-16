import type { AreaConfig, Genre } from "../config/parseMapConfig";
import type {
  LatLngBoundsLiteral,
  LatLngLiteral,
  PlaceLike,
  PlacesLibrary,
  SearchByTextRequest,
} from "../maps/googleTypes";
import type { Shop } from "./shop";

/** 1回の検索で取得する最大件数（無料利用枠を節約するため） */
export const MAX_RESULTS = 20;

/** 詳細パネルに必要な項目だけを取得する */
const FIELDS = [
  "id",
  "displayName",
  "formattedAddress",
  "location",
  "rating",
  "userRatingCount",
  "regularOpeningHours",
  "nationalPhoneNumber",
  "websiteURI",
  "googleMapsURI",
];

const METERS_PER_DEGREE_LAT = 111_000;

/** 中心から半径 radiusMeters の円を囲む矩形を返す（近似） */
export function boundsAround(center: LatLngLiteral, radiusMeters: number): LatLngBoundsLiteral {
  const dLat = radiusMeters / METERS_PER_DEGREE_LAT;
  const dLng = radiusMeters / (METERS_PER_DEGREE_LAT * Math.cos((center.lat * Math.PI) / 180));
  return {
    north: center.lat + dLat,
    south: center.lat - dLat,
    east: center.lng + dLng,
    west: center.lng - dLng,
  };
}

export function buildSearchRequest(genre: Genre, area: AreaConfig): SearchByTextRequest {
  return {
    textQuery: genre.query,
    fields: FIELDS,
    locationRestriction: boundsAround(area.center, area.radiusMeters),
    maxResultCount: MAX_RESULTS,
    language: "ja",
    region: "jp",
  };
}

/** http(s) の URL だけを通す（javascript: などのリンクを作らないため） */
function safeUrl(value: string | null | undefined): string | undefined {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:" ? url.toString() : undefined;
  } catch {
    return undefined;
  }
}

function fallbackMapsUrl(name: string, placeId: string): string {
  const url = new URL("https://www.google.com/maps/search/");
  url.search = new URLSearchParams({ api: "1", query: name, query_place_id: placeId }).toString();
  return url.toString();
}

/** Places API の Place を Shop に変換する。位置がない店舗は地図に置けないので null */
export function toShop(place: PlaceLike): Shop | null {
  if (!place.location) return null;
  const name = place.displayName?.trim() || "名称不明";
  const shop: Shop = {
    id: place.id,
    name,
    address: place.formattedAddress ?? "",
    location: { lat: place.location.lat(), lng: place.location.lng() },
    googleMapsUrl: safeUrl(place.googleMapsURI) ?? fallbackMapsUrl(name, place.id),
  };
  if (typeof place.rating === "number") shop.rating = place.rating;
  if (typeof place.userRatingCount === "number") shop.userRatingCount = place.userRatingCount;
  const hours = place.regularOpeningHours?.weekdayDescriptions;
  if (hours && hours.length > 0) shop.openingHours = [...hours];
  if (place.nationalPhoneNumber) shop.phoneNumber = place.nationalPhoneNumber;
  const website = safeUrl(place.websiteURI);
  if (website) shop.websiteUrl = website;
  return shop;
}

export type ShopSearcher = (genre: Genre) => Promise<Shop[]>;

/** ジャンルのクエリでエリア内の店舗を検索する関数を作る */
export function createShopSearcher(places: PlacesLibrary, area: AreaConfig): ShopSearcher {
  return async (genre) => {
    const { places: results } = await places.Place.searchByText(buildSearchRequest(genre, area));
    return results.map(toShop).filter((shop): shop is Shop => shop !== null);
  };
}
