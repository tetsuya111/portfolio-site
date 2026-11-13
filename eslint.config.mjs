// ESLint フラット設定（ESLint v9 以降の標準形式）
// 技術スタック確定後、TypeScript / React 等のプラグインをここに追加する。
import js from "@eslint/js";
import { defineConfig, globalIgnores } from "eslint/config";
import globals from "globals";

export default defineConfig([
  // ビルド成果物・依存パッケージは対象外
  globalIgnores(["node_modules/", "dist/", "build/", "out/", ".next/", "coverage/"]),

  {
    files: ["**/*.{js,mjs,cjs}"],
    plugins: { js },
    extends: ["js/recommended"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: { ...globals.browser },
    },
    linterOptions: {
      // 不要になった eslint-disable コメントを検出する
      reportUnusedDisableDirectives: "error",
    },
    rules: {
      "no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
      eqeqeq: ["error", "always"],
      "prefer-const": "error",
      "no-var": "error",
    },
  },

  // CommonJS ファイルと設定ファイルは Node.js 環境として扱う
  {
    files: ["**/*.cjs"],
    languageOptions: { sourceType: "commonjs", globals: { ...globals.node } },
  },
  {
    files: ["*.config.{js,mjs,cjs}"],
    languageOptions: { globals: { ...globals.node } },
  },
]);
