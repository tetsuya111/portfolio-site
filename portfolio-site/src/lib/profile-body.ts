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
  /** 自己紹介の段落 */
  intro: string[];
  career: CareerItem[];
  /** スキルの箇条書き1行ごとの、「 / 」で区切った技術 */
  skills: string[][];
  /** 資格の箇条書き1行ごとの、「 / 」で区切った資格 */
  certifications: string[][];
}

/** 描画すると Markdown の装飾・HTML・エスケープになりうる文字。そのまま文字として出すと内容が変わるため扱わない */
const DECORATION = /[[\]*`<>_|#&\\~]/;

/** 段落として読めない行（Markdown の箇条書き・区切り線・見出しの下線・字下げのコードなど） */
const NON_PARAGRAPH = /^(?:\s|[-+]\s|\d+[.)]\s|[-=]{3,}\s*$)/;

const LIST_ITEM = /^- (\S.*)$/;
const CAREER_ITEM = /^([^:：]{1,30}?)\s*[:：]\s*(\S.*)$/;

/** 内容を、末尾の（）より前と（）の中に分ける。末尾が（）でなければ詳細なし */
function splitDetails(content: string): { title: string; details: string[] } {
  if (!content.endsWith("）")) return { title: content, details: [] };
  let depth = 0;
  for (let i = content.length - 1; i >= 0; i--) {
    if (content[i] === "）") depth++;
    else if (content[i] === "（" && --depth === 0) {
      const title = content.slice(0, i).trim();
      if (!title) break;
      const details = content
        .slice(i + 1, -1)
        .split("、")
        .map((d) => d.trim())
        .filter((d) => d.length > 0);
      return { title, details };
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
    if (!m) return null;
    items.push((m[1] as string).trim());
  }
  return items;
}

function paragraphs(lines: string[]): string[] | null {
  const result: string[] = [];
  let current: string[] = [];
  for (const line of [...lines, ""]) {
    if (line.trim() === "") {
      if (current.length > 0) result.push(current.join(""));
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
    const h2 = /^## (.+)$/.exec(line);
    const h3 = /^### (.+)$/.exec(line);
    if (h2 || h3) {
      const name = ((h2 ?? h3) as RegExpExecArray)[1]?.trim() as string;
      const key = h2 ? name : `${name}#h3`;
      if (!["自己紹介", "経歴", "スキル", "資格#h3"].includes(key) || sections.has(key)) return null;
      // 資格はスキルの節の中にだけ置ける
      if (key === "資格#h3" && !sections.has("スキル")) return null;
      current = [];
      sections.set(key, current);
      continue;
    }
    if (current) current.push(line);
    else if (line.trim() !== "") return null;
  }
  // スキルの後に別の ## が来たら、資格はスキルの節の中ではない
  const keys = [...sections.keys()];
  const certIndex = keys.indexOf("資格#h3");
  if (certIndex !== -1 && keys[certIndex - 1] !== "スキル") return null;

  const intro = paragraphs(sections.get("自己紹介") ?? []);
  const careerLines = listItems(sections.get("経歴") ?? []);
  const skillLines = listItems(sections.get("スキル") ?? []);
  const certLines = listItems(sections.get("資格#h3") ?? []);
  if (!intro || !careerLines || !skillLines || !certLines) return null;

  const career: CareerItem[] = [];
  for (const line of careerLines) {
    const m = CAREER_ITEM.exec(line);
    if (!m) return null;
    career.push({ period: (m[1] as string).trim(), ...splitDetails((m[2] as string).trim()) });
  }
  const skills = skillLines.map(splitSlash);
  const certifications = certLines.map(splitSlash);

  if (intro.length + career.length + skills.length + certifications.length === 0) return null;
  return { intro, career, skills, certifications };
}
