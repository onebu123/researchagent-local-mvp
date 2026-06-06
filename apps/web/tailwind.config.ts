import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "Microsoft YaHei", "sans-serif"]
      },
      boxShadow: {
        panel: "0 16px 40px rgba(27, 39, 77, 0.08)"
      }
    }
  },
  plugins: []
};

export default config;
