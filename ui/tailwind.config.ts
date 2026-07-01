import type { Config } from "tailwindcss";

// Direction artistique : HUD "Stark Industries".
// Fond quasi noir, accents cyan + ambre, typo mono pour les données.
const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        hud: {
          bg: "#0a0e14",
          panel: "#0f1621",
          border: "#1c2735",
          cyan: "#22d3ee",
          amber: "#f59e0b",
          green: "#34d399",
          red: "#f87171",
          gray: "#64748b",
          muted: "#94a3b8",
          text: "#e2e8f0",
        },
      },
      fontFamily: {
        mono: [
          "JetBrains Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "monospace",
        ],
      },
      boxShadow: {
        glow: "0 0 20px -6px rgba(34, 211, 238, 0.4)",
        "glow-amber": "0 0 20px -6px rgba(245, 158, 11, 0.4)",
      },
      backdropBlur: {
        xs: "2px",
      },
      keyframes: {
        pulseGlow: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.55" },
        },
      },
      animation: {
        "pulse-glow": "pulseGlow 2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
