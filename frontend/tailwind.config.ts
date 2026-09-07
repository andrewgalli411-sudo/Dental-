import type { Config } from "tailwindcss";

// Verifi UI Kit tokens (see design/ui-kit.html). Clinical, light-only.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#F7F8FA",
        surface: "#FFFFFF",
        surfacealt: "#F2F4F7",
        border: "#DFE3E8",
        borderstrong: "#C3C9D2",
        ink: "#1A2027",
        ink2: "#49525D",
        ink3: "#6B7480",
        accent: { DEFAULT: "#2A5C8A", hover: "#21496E", weak: "#EAF0F6" },
        ok: { ink: "#0F7A52", bg: "#E7F4EE", bd: "#BFE3D0" },
        bad: { ink: "#B42318", bg: "#FCEBEA", bd: "#F4C6C2" },
        warn: { ink: "#B45309", bg: "#FDF3E7", bd: "#F5D9B0" },
      },
      borderRadius: { sm: "3px", DEFAULT: "3px", md: "6px" },
      fontFamily: {
        sans: ["'IBM Plex Sans'", "-apple-system", "BlinkMacSystemFont", "'Segoe UI'", "Roboto", "Arial", "sans-serif"],
        mono: ["'IBM Plex Mono'", "ui-monospace", "Menlo", "Consolas", "monospace"],
      },
      fontSize: {
        "11": ["11px", "1.3"],
        "12": ["12px", "1.4"],
        "13": ["13px", "1.45"],
        "14": ["14px", "1.5"],
        "15": ["15px", "1.4"],
        "18": ["18px", "1.3"],
        "22": ["22px", "1.25"],
        "28": ["28px", "1.2"],
      },
    },
  },
  plugins: [],
};

export default config;
