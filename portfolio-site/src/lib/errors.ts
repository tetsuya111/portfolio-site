/** 入力（スラッグ・frontmatter・コマンド引数）が不正なときのエラー。API では 400 に対応する。 */
export class ContentValidationError extends Error {
  readonly issues: string[];

  constructor(issues: string[]) {
    super(issues.join(" / "));
    this.name = "ContentValidationError";
    this.issues = issues;
  }
}

/** 作成しようとしたファイルが既に存在するときのエラー。API では 409 に対応する。 */
export class ContentConflictError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ContentConflictError";
  }
}
