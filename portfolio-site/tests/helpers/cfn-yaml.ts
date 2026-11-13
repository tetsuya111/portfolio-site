// CloudFormation テンプレートを読み込む。短縮形の組み込み関数（!Ref・!Sub など）を
// 正式な形（{ Ref: ... }・{ "Fn::Sub": ... }）に変換する。
import { readFileSync } from "node:fs";
import { parse, type ScalarTag, type CollectionTag } from "yaml";

const FUNCTIONS = [
  "And", "Base64", "Cidr", "Equals", "FindInMap", "GetAtt", "GetAZs", "If", "ImportValue",
  "Join", "Not", "Or", "Select", "Split", "Sub", "Contains", "EachMemberEquals", "RefAll",
  "ValueOf", "ValueOfAll",
];

function toObject(name: string, value: unknown): unknown {
  if (name === "Ref") return { Ref: value };
  if (name === "GetAtt" && typeof value === "string") {
    const i = value.indexOf(".");
    return { "Fn::GetAtt": [value.slice(0, i), value.slice(i + 1)] };
  }
  return { [`Fn::${name}`]: value };
}

function tagsFor(name: string): (ScalarTag | CollectionTag)[] {
  const tag = `!${name}`;
  return [
    { tag, resolve: (v: string) => toObject(name, v) } as ScalarTag,
    { tag, collection: "seq", resolve: (v: { toJSON(): unknown }) => toObject(name, v.toJSON()) } as unknown as CollectionTag,
    { tag, collection: "map", resolve: (v: { toJSON(): unknown }) => toObject(name, v.toJSON()) } as unknown as CollectionTag,
  ];
}

const customTags = ["Ref", ...FUNCTIONS].flatMap(tagsFor);

// テンプレートの構造は自由形式のため any で返す
export function loadCfnTemplate(path: string): any {
  return parse(readFileSync(path, "utf8"), { customTags });
}
