import { describe, expect, test } from "vitest";
import bundledConfig from "./map-config.json";
import { ConfigError, parseMapConfig } from "./parseMapConfig";

const valid = () => ({
  area: {
    name: "新宿",
    center: { lat: 35.6896, lng: 139.7006 },
    radiusMeters: 1500,
    zoom: 15,
  },
  genres: [
    { id: "ramen", label: "ラーメン", query: "新宿 ラーメン", icon: "🍜" },
    { id: "cafe", label: "カフェ", query: "新宿 カフェ" },
  ],
});

function problemsOf(raw: unknown): string[] {
  try {
    parseMapConfig(raw);
  } catch (e) {
    if (e instanceof ConfigError) return e.problems;
    throw e;
  }
  throw new Error("ConfigError が投げられなかった");
}

describe("parseMapConfig", () => {
  test("正しい設定はそのまま型付きで返る", () => {
    const config = parseMapConfig(valid());
    expect(config.area.center).toEqual({ lat: 35.6896, lng: 139.7006 });
    expect(config.genres.map((g) => g.id)).toEqual(["ramen", "cafe"]);
    expect(config.genres[0].icon).toBe("🍜");
    expect(config.genres[1].icon).toBeUndefined();
  });

  test("オブジェクトでなければエラー", () => {
    expect(problemsOf(null)).toEqual(["設定ファイルの最上位はオブジェクトにしてください"]);
  });

  test("ジャンルが0件ならエラー", () => {
    expect(problemsOf({ ...valid(), genres: [] })).toContain("genres: ジャンルを1件以上定義してください");
  });

  test("id の重複を報告する", () => {
    const raw = valid();
    raw.genres[1].id = "ramen";
    expect(problemsOf(raw)).toContain('genres[1].id: "ramen" が重複しています');
  });

  test("id の形式が不正なら報告する", () => {
    const raw = valid();
    raw.genres[0].id = "Ramen Shop";
    expect(problemsOf(raw)).toContain("genres[0].id: 英小文字・数字・ハイフンで指定してください");
  });

  test("label・query が空なら報告する", () => {
    const raw = valid();
    raw.genres[0].label = "  ";
    raw.genres[1].query = "";
    const problems = problemsOf(raw);
    expect(problems).toContain("genres[0].label: 空でない文字列を指定してください");
    expect(problems).toContain("genres[1].query: 空でない文字列を指定してください");
  });

  test("icon が文字列でなければ報告する", () => {
    const raw = { ...valid(), genres: [{ id: "a", label: "A", query: "A", icon: 1 }] };
    expect(problemsOf(raw)).toContain("genres[0].icon: 文字列を指定してください");
  });

  test("緯度・経度が範囲外なら報告する", () => {
    const raw = valid();
    raw.area.center = { lat: 86, lng: -181 };
    const problems = problemsOf(raw);
    expect(problems).toContain("area.center.lat: -85〜85 の数値を指定してください");
    expect(problems).toContain("area.center.lng: -180〜180 の数値を指定してください");
  });

  test("半径・ズームが範囲外なら報告する", () => {
    const raw = valid();
    raw.area.radiusMeters = 0;
    raw.area.zoom = 22;
    const problems = problemsOf(raw);
    expect(problems).toContain("area.radiusMeters: 1〜50000 の数値を指定してください");
    expect(problems).toContain("area.zoom: 1〜21 の数値を指定してください");
  });

  test("area.name が空なら報告する", () => {
    const raw = valid();
    raw.area.name = "";
    expect(problemsOf(raw)).toContain("area.name: 空でない文字列を指定してください");
  });

  test("area がなければ報告する", () => {
    const { genres } = valid();
    expect(problemsOf({ genres })).toContain("area: オブジェクトを指定してください");
  });

  test("複数の違反をまとめて報告し、メッセージにも含める", () => {
    const raw = valid();
    raw.area.zoom = 0;
    raw.genres[0].label = "";
    const error = (() => {
      try {
        parseMapConfig(raw);
      } catch (e) {
        return e as ConfigError;
      }
    })();
    expect(error?.problems).toHaveLength(2);
    expect(error?.message).toContain("area.zoom");
    expect(error?.message).toContain("genres[0].label");
  });

  test("同梱の map-config.json は検証を通る", () => {
    const config = parseMapConfig(bundledConfig);
    expect(config.genres.length).toBeGreaterThan(0);
  });
});
