import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const frontendDir = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  base: "/static/dist/",
  plugins: [react()],
  build: {
    outDir: "static/dist",
    emptyOutDir: false,
    rollupOptions: {
      input: resolve(frontendDir, "src/main.jsx"),
      output: {
        entryFileNames: "icm.js",
        assetFileNames: "icm.[ext]",
      },
    },
  },
});
