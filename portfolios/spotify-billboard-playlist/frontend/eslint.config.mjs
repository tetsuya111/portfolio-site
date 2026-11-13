import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const config = [
  ...nextVitals,
  ...nextTs,
  { ignores: [".next/**", "node_modules/**", "next-env.d.ts"] },
  // リポジトリのルートから eslint を実行しても app/ を正しく見つけられるようにする
  { settings: { next: { rootDir: import.meta.dirname } } },
];

export default config;
