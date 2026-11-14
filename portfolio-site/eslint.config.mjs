// ESLint フラット設定（portfolio-site 専用。ルートの設定はこのディレクトリを対象外にしている）
import js from "@eslint/js";
import astro from "eslint-plugin-astro";
import { defineConfig, globalIgnores } from "eslint/config";
import globals from "globals";
import tseslint from "typescript-eslint";

export default defineConfig([
  // apps/ はポートフォリオのフロントエンド。各アプリが独自の lint 設定を持つため検査しない
  globalIgnores(["dist/", ".astro/", "node_modules/", "apps/"]),
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...astro.configs.recommended,
  {
    linterOptions: { reportUnusedDisableDirectives: "error" },
    rules: {
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
      eqeqeq: ["error", "always"],
      "prefer-const": "error",
      "no-var": "error",
    },
  },
  // Node.js で動くファイル（コマンド・インテグレーション・設定・テスト）
  {
    files: ["scripts/**", "integrations/**", "tests/**", "*.config.{js,mjs,ts}"],
    languageOptions: { globals: { ...globals.node } },
  },
  // 管理画面のブラウザ側スクリプト
  {
    files: ["src/admin/**", "src/lib/mock-runtime.js"],
    languageOptions: { globals: { ...globals.browser } },
  },
  // テンプレートの構造を自由形式で扱うテストでは any を許可する
  {
    files: ["tests/**"],
    rules: { "@typescript-eslint/no-explicit-any": "off" },
  },
]);
