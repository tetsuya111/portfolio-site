// @ts-check
import { defineConfig } from "astro/config";
import tailwindcss from "@tailwindcss/vite";

// https://docs.astro.build/en/reference/configuration-reference/
export default defineConfig({
  output: "static",
  trailingSlash: "always",
  vite: { plugins: [tailwindcss()] },
});
