/** Google Maps JavaScript API の読み込み（使う部分だけの最小限の型）。 */

export type LatLng = { lat: number; lng: number };

export type MapInstance = {
  fitBounds(bounds: unknown): void;
  setCenter(p: LatLng): void;
  setZoom(z: number): void;
};

export type MarkerInstance = {
  addListener(event: "click", handler: () => void): void;
  setMap(map: MapInstance | null): void;
};

export type MapsApi = {
  Map: new (el: HTMLElement, options: Record<string, unknown>) => MapInstance;
  Marker: new (options: { position: LatLng; map: MapInstance; title: string }) => MarkerInstance;
  LatLngBounds: new () => { extend(p: LatLng): void };
};

export type MapsLoader = (apiKey: string) => Promise<MapsApi>;

declare global {
  interface Window {
    google?: { maps?: MapsApi };
    __avEventDbMapsReady?: () => void;
  }
}

let loading: Promise<MapsApi> | null = null;

export const loadGoogleMaps: MapsLoader = (apiKey) => {
  if (window.google?.maps) return Promise.resolve(window.google.maps);
  if (loading) return loading;
  loading = new Promise<MapsApi>((resolve, reject) => {
    window.__avEventDbMapsReady = () => {
      if (window.google?.maps) resolve(window.google.maps);
      else reject(new Error("Google Maps を読み込めませんでした。"));
    };
    const script = document.createElement("script");
    const params = new URLSearchParams({
      key: apiKey,
      callback: "__avEventDbMapsReady",
      language: "ja",
      region: "JP",
    });
    script.src = `https://maps.googleapis.com/maps/api/js?${params}`;
    script.async = true;
    script.onerror = () => {
      loading = null;
      reject(new Error("Google Maps を読み込めませんでした。"));
    };
    document.head.appendChild(script);
  });
  return loading;
};
