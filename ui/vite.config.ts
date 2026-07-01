/// <reference types="vitest/config" />
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// Base API du backend jarvis-suit (FastAPI). Configurable via VITE_API_BASE.
// Un proxy dev renvoie /api (REST) et /ws (WebSocket) vers cette base, ce qui
// évite le CORS en développement et garde le même origin côté front.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiBase = env.VITE_API_BASE || "http://127.0.0.1:8000";
  const wsBase = apiBase.replace(/^http/, "ws");

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: apiBase,
          changeOrigin: true,
        },
        "/ws": {
          target: wsBase,
          ws: true,
          changeOrigin: true,
        },
      },
    },
    test: {
      globals: true,
      environment: "jsdom",
      setupFiles: ["./src/test/setup.ts"],
      css: false,
    },
  };
});
