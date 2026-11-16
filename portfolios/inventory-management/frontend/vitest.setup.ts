// globals: true のため afterEach はグローバルを使う（Windows でドライブ文字の大文字・小文字が
// 異なる作業ディレクトリから実行したとき、"vitest" を import すると別インスタンスになるのを避ける）。
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";

import { clearToken } from "./src/lib/api";

afterEach(() => {
  cleanup();
  clearToken(); // localStorage とメモリーのトークンを消す
  localStorage.clear();
});
