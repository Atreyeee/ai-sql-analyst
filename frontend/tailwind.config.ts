import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "#0B0D12", // page background
          panel: "#15181F", // raised panel surface
          line: "#242833", // hairline rule
        },
        ivory: {
          DEFAULT: "#F3F1EA", // primary text
          dim: "#9A9686", // secondary text
        },
        amber: {
          DEFAULT: "#E2A23B", // the single accent — used sparingly
          dim: "#7A5A26",
        },
        signal: {
          ok: "#7FB77E",
          error: "#D9695F",
        },
      },
      fontFamily: {
        display: ["var(--font-fraunces)", "ui-serif", "Georgia", "serif"],
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-jbmono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      letterSpacing: {
        tightish: "-0.01em",
      },
      maxWidth: {
        measure: "72ch",
      },
      keyframes: {
        "pulse-soft": {
          "0%, 100%": { opacity: "0.35" },
          "50%": { opacity: "0.9" },
        },
      },
      animation: {
        "pulse-soft": "pulse-soft 1.8s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
