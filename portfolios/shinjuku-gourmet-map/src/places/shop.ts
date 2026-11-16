import type { LatLngLiteral } from "../maps/googleTypes";

/** 地図に表示する店舗 */
export interface Shop {
  id: string;
  name: string;
  address: string;
  location: LatLngLiteral;
  rating?: number;
  userRatingCount?: number;
  /** 曜日ごとの営業時間（例: "月曜日: 11時00分～22時00分"） */
  openingHours?: string[];
  phoneNumber?: string;
  websiteUrl?: string;
  googleMapsUrl: string;
}
