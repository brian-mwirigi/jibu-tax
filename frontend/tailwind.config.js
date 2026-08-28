/**
 * File: frontend/tailwind.config.js
 * Description:
 *   Tailwind CSS Design System Configuration.
 *   - Defines content paths for React components (./index.html, ./src/**\/*.{js,jsx}).
 *   - Customizes theme colors, Kenyan national color palette accents, and typography.
 */

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        kra: {
          red: "#D32F2F",
          green: "#2E7D32",
          dark: "#1B1B1B",
        },
      },
    },
  },
  plugins: [],
};
