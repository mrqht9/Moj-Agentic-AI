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
        primary: "#0db9f2",
        "background-light": "#f5f8f8",
        "background-dark": "#101e22",
        "sidebar-light": "#f0f4f6",
        "sidebar-dark": "#0d181c",
      },
      fontFamily: {
        display: ["Inter", "sans-serif"],
        mono: ["Fira Code", "monospace"],
      },
    },
  },
  plugins: [],
}
