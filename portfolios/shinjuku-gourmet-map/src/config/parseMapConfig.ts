/** 緯度・経度 */
export interface LatLng {
  lat: number;
  lng: number;
}

/** 検索対象エリア */
export interface AreaConfig {
  name: string;
  center: LatLng;
  radiusMeters: number;
  zoom: number;
}

/** ジャンル（ボタン1つ分） */
export interface Genre {
  id: string;
  label: string;
  query: string;
  icon?: string;
}

export interface MapConfig {
  area: AreaConfig;
  genres: Genre[];
}

/** 設定ファイルの内容が不正なときに投げる。problems に違反を列挙する */
export class ConfigError extends Error {
  readonly problems: string[];

  constructor(problems: string[]) {
    super(`設定ファイル（map-config.json）に誤りがあります:\n${problems.join("\n")}`);
    this.name = "ConfigError";
    this.problems = problems;
  }
}

const ID_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

type PlainObject = Record<string, unknown>;

const isObject = (v: unknown): v is PlainObject =>
  typeof v === "object" && v !== null && !Array.isArray(v);

/**
 * 設定ファイルの内容を検証し、型付きの設定を返す。
 * 違反があれば、すべてを集めて ConfigError を投げる。
 */
export function parseMapConfig(raw: unknown): MapConfig {
  if (!isObject(raw)) {
    throw new ConfigError(["設定ファイルの最上位はオブジェクトにしてください"]);
  }
  const problems: string[] = [];

  const text = (v: unknown, path: string): string => {
    if (typeof v === "string" && v.trim() !== "") return v.trim();
    problems.push(`${path}: 空でない文字列を指定してください`);
    return "";
  };
  const numberIn = (v: unknown, min: number, max: number, path: string): number => {
    if (typeof v === "number" && Number.isFinite(v) && v >= min && v <= max) return v;
    problems.push(`${path}: ${min}〜${max} の数値を指定してください`);
    return min;
  };

  let area: AreaConfig = { name: "", center: { lat: 0, lng: 0 }, radiusMeters: 1, zoom: 1 };
  if (!isObject(raw.area)) {
    problems.push("area: オブジェクトを指定してください");
  } else {
    const center = isObject(raw.area.center) ? raw.area.center : {};
    if (!isObject(raw.area.center)) problems.push("area.center: オブジェクトを指定してください");
    area = {
      name: text(raw.area.name, "area.name"),
      center: {
        // 極付近は検索範囲の計算（経度方向の幅）が発散するため除外する
        lat: numberIn(center.lat, -85, 85, "area.center.lat"),
        lng: numberIn(center.lng, -180, 180, "area.center.lng"),
      },
      radiusMeters: numberIn(raw.area.radiusMeters, 1, 50000, "area.radiusMeters"),
      zoom: numberIn(raw.area.zoom, 1, 21, "area.zoom"),
    };
  }

  const genres: Genre[] = [];
  if (!Array.isArray(raw.genres) || raw.genres.length === 0) {
    problems.push("genres: ジャンルを1件以上定義してください");
  } else {
    const seen = new Set<string>();
    raw.genres.forEach((g: unknown, i: number) => {
      const path = `genres[${i}]`;
      if (!isObject(g)) {
        problems.push(`${path}: オブジェクトを指定してください`);
        return;
      }
      let id = "";
      if (typeof g.id !== "string" || !ID_PATTERN.test(g.id)) {
        problems.push(`${path}.id: 英小文字・数字・ハイフンで指定してください`);
      } else if (seen.has(g.id)) {
        problems.push(`${path}.id: "${g.id}" が重複しています`);
      } else {
        id = g.id;
        seen.add(id);
      }
      const genre: Genre = {
        id,
        label: text(g.label, `${path}.label`),
        query: text(g.query, `${path}.query`),
      };
      if (g.icon !== undefined) {
        if (typeof g.icon === "string") genre.icon = g.icon;
        else problems.push(`${path}.icon: 文字列を指定してください`);
      }
      genres.push(genre);
    });
  }

  if (problems.length > 0) throw new ConfigError(problems);
  return { area, genres };
}
