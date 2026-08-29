/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        kra: {
          red: "#D32F2F",
          green: "#2E7D32",
          dark: "#1B1B1B",
          gold: "#F59E0B",
          emerald: "#10B981",
          crimson: "#EF4444",
          slate: "#0B0F17",
          surface: "#18181B",
          card: "#121214",
          border: "#27272A",
          accent: "#22C55E",
          cyan: "#06B6D4",
        },
      },
    },
  },
  plugins: [],
};
