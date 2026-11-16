/**
 * このアプリが使う Google Maps JavaScript API の最小限の型。
 * （@types/google.maps に依存しないため、利用する範囲だけを定義する）
 */

export interface LatLngLiteral {
  lat: number;
  lng: number;
}

/** google.maps.LatLng（lat()/lng() で値を取り出す） */
export interface LatLngObject {
  lat(): number;
  lng(): number;
}

export interface LatLngBoundsLiteral {
  north: number;
  south: number;
  east: number;
  west: number;
}

export interface LatLngBoundsObject {
  extend(point: LatLngLiteral): unknown;
}

export interface MapListener {
  remove(): void;
}

export interface GoogleMap {
  fitBounds(bounds: LatLngBoundsObject, padding?: number): void;
  panTo(point: LatLngLiteral): void;
  setZoom(zoom: number): void;
}

export interface MapOptions {
  center: LatLngLiteral;
  zoom: number;
  mapId: string;
  clickableIcons?: boolean;
  gestureHandling?: string;
}

export interface MapsLibrary {
  Map: new (element: HTMLElement, options: MapOptions) => GoogleMap;
}

export interface CoreLibrary {
  LatLngBounds: new () => LatLngBoundsObject;
}

export interface AdvancedMarkerOptions {
  map: GoogleMap;
  position: LatLngLiteral;
  title: string;
  content: HTMLElement;
  gmpClickable: boolean;
}

export interface AdvancedMarker {
  map: GoogleMap | null;
  addListener(event: "click", handler: () => void): MapListener;
}

export interface MarkerLibrary {
  AdvancedMarkerElement: new (options: AdvancedMarkerOptions) => AdvancedMarker;
}

/** Places API (New) の Place（取得したフィールドのみ値が入る） */
export interface PlaceLike {
  id: string;
  displayName?: string | null;
  formattedAddress?: string | null;
  location?: LatLngObject | null;
  rating?: number | null;
  userRatingCount?: number | null;
  regularOpeningHours?: { weekdayDescriptions?: string[] | null } | null;
  nationalPhoneNumber?: string | null;
  websiteURI?: string | null;
  googleMapsURI?: string | null;
}

export interface SearchByTextRequest {
  textQuery: string;
  fields: string[];
  locationRestriction: LatLngBoundsLiteral;
  maxResultCount: number;
  language: string;
  region: string;
}

export interface PlacesLibrary {
  Place: {
    searchByText(request: SearchByTextRequest): Promise<{ places: PlaceLike[] }>;
  };
}

export interface GoogleLibraries {
  core: CoreLibrary;
  maps: MapsLibrary;
  marker: MarkerLibrary;
  places: PlacesLibrary;
}
