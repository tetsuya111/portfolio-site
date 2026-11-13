import { ContentValidationError } from "./errors";

/** ファイル名に使うスラッグ。英小文字・数字を単一のハイフンでつないだ 1〜64 文字。 */
const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const MAX_SLUG_LENGTH = 64;

export function isValidSlug(slug: string): boolean {
  return slug.length <= MAX_SLUG_LENGTH && SLUG_RE.test(slug);
}

/** 不正なスラッグなら ContentValidationError を投げる。パスを組み立てる前に必ず呼ぶ。 */
export function assertValidSlug(slug: string): void {
  if (!isValidSlug(slug)) {
    throw new ContentValidationError([
      `スラッグ「${slug}」は不正です（英小文字・数字・ハイフンのみ、1〜${MAX_SLUG_LENGTH}文字）`,
    ]);
  }
}
