// トップページの相談ボタン（コンタクトフォーム・タスク百葉箱）の設定を、ビルド時の環境変数とサイト設定から決める。
// 判定をここに集め、ページ（index.astro）とフォームの送信処理（ConsultCta.astro）から使う。
import { z } from "astro/zod";
import { isLinkTarget } from "./schemas";

/** z.email() は ? & などを含むアドレスを拒否するため、mailto: にヘッダー（bcc など）を差し込まれない */
const email = z.email();

export interface ConsultationEnv {
  /** PUBLIC_CONTACT_EMAIL: コンタクトフォームの宛先 */
  contactEmail?: string | undefined;
  /** PUBLIC_TASK_BOX_URL: タスク百葉箱の URL */
  taskBoxUrl?: string | undefined;
}

export interface Consultation {
  /** 有効な宛先。null ならフォームのボタンを出さない */
  contactEmail: string | null;
  /** タスク百葉箱の遷移先。null ならボタンを無効にする */
  taskBox: { href: string; external: boolean } | null;
}

/**
 * 宛先は環境変数が有効なメールアドレスのときだけ使う。
 * タスク百葉箱は 環境変数 → サイト設定のモック URL の順に、リンクにできる最初の値を使う。
 */
export function resolveConsultation(env: ConsultationEnv, config: { taskBoxMockUrl?: string | undefined }): Consultation {
  const address = env.contactEmail?.trim();
  const contactEmail = address && email.safeParse(address).success ? address : null;
  const href = [env.taskBoxUrl?.trim(), config.taskBoxMockUrl?.trim()].find(
    (v): v is string => !!v && isLinkTarget(v),
  );
  return {
    contactEmail,
    taskBox: href ? { href, external: /^https?:/i.test(href) } : null,
  };
}
