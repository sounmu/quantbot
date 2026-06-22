import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./hooks/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17212b",
        muted: "#64748b",
        panel: "#f8fafc",
        line: "#d7dee8",
        accent: "#0f766e",
        cobalt: "#2563eb",
        berry: "#be185d"
      },
      boxShadow: {
        soft: "0 8px 24px rgba(23, 33, 43, 0.08)"
      }
    }
  },
  plugins: []
};

export default config;

