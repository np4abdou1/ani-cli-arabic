/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#08090d",
        surface: "#10121a",
        card: "#141724",
        border: "#202538",
        primary: {
          DEFAULT: "#7aa2f7",
          glow: "#3d59a1",
          hover: "#89b4fa"
        },
        accent: {
          cyan: "#7dcfff",
          green: "#9ece6a",
          yellow: "#e0af68",
          magenta: "#bb9af7",
          pink: "#f7768e"
        }
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "glow": "glow 2s ease-in-out infinite alternate"
      },
      keyframes: {
        glow: {
          "0%": { boxShadow: "0 0 10px rgba(122, 162, 247, 0.2)" },
          "100%": { boxShadow: "0 0 25px rgba(122, 162, 247, 0.6)" }
        }
      }
    },
  },
  plugins: [],
};
