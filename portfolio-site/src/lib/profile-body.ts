// profile.md の本文を、自己紹介ページのデザイン（タイムライン・タグ）用に読み取る。
// スキルシート取り込み・管理画面が書く決まった書式（## 自己紹介 / ## 経歴 / ## スキル / ### 資格）だけを扱い、
// それ以外の書式や Markdown の装飾を含むときは null を返す（呼び出し側は本文を Markdown のまま表示する）。

export interface CareerItem {
  /** 例: 2022年〜2023年 */
  period: string;
  /** 内容のうち、末尾の（）より前 */
  title: string;
  /** 末尾の（）の中を「、」で区切ったもの */
  details: string[];
}

export interface ProfileBody {
  /** 自己紹介の段落（段落内の改行は \n のまま。HTML では空白として表示される） */
  intro: string[];
  career: CareerItem[];
  /** スキルの箇条書き1行ごとの、「 / 」で区切った技術 */
  skills: string[][];
  /** 資格の箇条書き1行ごとの、「 / 」で区切った資格 */
  certifications: string[][];
}

/**
 * 描画すると Markdown の装飾・HTML・エスケープ・自動リンク・記号の置き換え（smartypants の引用符・ダッシュ・三点リーダー）
 * になりうるもの（行頭の # は見出し、& は文字参照のときだけ、@ はメールアドレスの形のときだけ。行末の2つ以上の空白は強制改行）。
 * そのまま文字として出すと Markdown の表示と変わるため扱わない。C#・R&D のような文中の # & はそのまま文字になるので受け付ける
 */
const DECORATION =
  /[[\]*`<>_|\\~"']|^#|&(?:#\d+|#x[0-9a-f]+|[a-z][a-z0-9]*);|[^\s@]+@[^\s@]+\.[^\s@]+|--|\.\.\.|:\/\/|www\.| {2,}$/im;

/** 段落として読めない行（Markdown の箇条書き・区切り線・見出しの下線・字下げのコードなど） */
const NON_PARAGRAPH = /^(?:\s|(?:[-+]|\d+[.)])(?:\s|$)|[-=]+\s*$)/;

/** 受け付ける見出し。この順でしか受け付けない（ページもこの順で描くため）。資格はスキルの節の中の ### */
const SECTION_ORDER = ["自己紹介", "経歴", "スキル", "資格#h3"];

const LIST_ITEM = /^- (\S.*)$/;
/** 箇条書きの中身の先頭が、さらに箇条書きの記号（入れ子のリストになる） */
const NESTED_MARKER = /^(?:[-+*]|\d+[.)])(?:\s|$)/;
const CAREER_ITEM = /^([^:：]{1,30}?)\s*[:：]\s*(\S.*)$/;

/** 「、」で区切る。入れ子の（）・()の中の「、」では区切らない */
function splitTopLevel(text: string): string[] {
  const parts: string[] = [];
  let depth = 0;
  let current = "";
  for (const ch of text) {
    if (ch === "（" || ch === "(") depth++;
    else if (ch === "）" || ch === ")") depth = Math.max(0, depth - 1);
    if (ch === "、" && depth === 0) {
      parts.push(current);
      current = "";
    } else current += ch;
  }
  parts.push(current);
  return parts.map((d) => d.trim()).filter((d) => d.length > 0);
}

/** 内容を、末尾の（）・()より前とその中に分ける。末尾が括弧でなければ詳細なし */
function splitDetails(content: string): { title: string; details: string[] } {
  if (!content.endsWith("）") && !content.endsWith(")")) return { title: content, details: [] };
  let depth = 0;
  for (let i = content.length - 1; i >= 0; i--) {
    if (content[i] === "）" || content[i] === ")") depth++;
    else if ((content[i] === "（" || content[i] === "(") && --depth === 0) {
      const title = content.slice(0, i).trim();
      if (!title) break;
      return { title, details: splitTopLevel(content.slice(i + 1, -1)) };
    }
  }
  return { title: content, details: [] };
}

const splitSlash = (s: string) =>
  s
    .split(/\s+\/\s+/)
    .map((x) => x.trim())
    .filter((x) => x.length > 0);

/** 節の箇条書きの中身を返す。空行は飛ばし、箇条書きでない行があれば null */
function listItems(lines: string[]): string[] | null {
  const items: string[] = [];
  for (const line of lines) {
    if (line.trim() === "") continue;
    const m = LIST_ITEM.exec(line.trimEnd());
    if (!m || NESTED_MARKER.test(m[1] as string)) return null;
    items.push((m[1] as string).trim());
  }
  return items;
}

function paragraphs(lines: string[]): string[] | null {
  const result: string[] = [];
  let current: string[] = [];
  for (const line of [...lines, ""]) {
    if (line.trim() === "") {
      if (current.length > 0) result.push(current.join("\n"));
      current = [];
      continue;
    }
    if (NON_PARAGRAPH.test(line)) return null;
    current.push(line.trim());
  }
  return result;
}

export function parseProfileBody(body: string): ProfileBody | null {
  if (DECORATION.test(body.replace(/^#{2,3} .*$/gm, ""))) return null;

  // 見出し（## ・### 資格）ごとに行を集める。最初の見出しより前に文があれば扱わない
  const sections = new Map<string, string[]>();
  let current: string[] | null = null;
  for (const line of body.split(/\r?\n/)) {
    const h = /^(##|###) (.+)$/.exec(line);
    if (h) {
      const name = (h[2] as string).trim();
      const key = h[1] === "##" ? name : `${name}#h3`;
      // 未知の見出し・重複・順序違い（資格がスキルの直後でないものを含む）は扱わない
      const last = [...sections.keys()].pop();
      if (!SECTION_ORDER.includes(key)) return null;
      if (last !== undefined && SECTION_ORDER.indexOf(key) <= SECTION_ORDER.indexOf(last)) return null;
      if (key === "資格#h3" && last !== "スキル") return null;
      current = [];
      sections.set(key, current);
      continue;
    }
    if (current) current.push(line);
    else if (line.trim() !== "") return null;
  }
  if (sections.size === 0) return null;

  const intro = paragraphs(sections.get("自己紹介") ?? []);
  const careerLines = listItems(sections.get("経歴") ?? []);
  const skillLines = listItems(sections.get("スキル") ?? []);
  const certLines = listItems(sections.get("資格#h3") ?? []);
  if (!intro || !careerLines || !skillLines || !certLines) return null;

  // 見出しだけで中身のない節は、新しいデザインでは見出しが消えるため Markdown のまま表示する
  const counts: Record<string, number> = {
    自己紹介: intro.length,
    経歴: careerLines.length,
    スキル: skillLines.length,
    "資格#h3": certLines.length,
  };
  if ([...sections.keys()].some((k) => counts[k] === 0)) return null;

  const career: CareerItem[] = [];
  for (const line of careerLines) {
    const m = CAREER_ITEM.exec(line);
    if (!m) return null;
    career.push({ period: (m[1] as string).trim(), ...splitDetails((m[2] as string).trim()) });
  }
  return { intro, career, skills: skillLines.map(splitSlash), certifications: certLines.map(splitSlash) };
}
