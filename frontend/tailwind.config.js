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
        primary: "#00BCD4",
        secondary: "#0891B2",
        "background-light": "#F7F9FC",
        "background-dark": "#0A1929",
        "sidebar-light": "#FFFFFF",
        "sidebar-dark": "#0D1B2A",
        "card-light": "#FFFFFF",
        "card-dark": "#162536",
        "border-light": "#E5E7EB",
        "border-dark": "#1E3A52",
        "text-primary-light": "#2D3748",
        "text-primary-dark": "#F9FAFB",
        "text-secondary-light": "#6B7280",
        "text-secondary-dark": "#9CA3AF",
      },
      fontFamily: {
        display: ["Inter", "sans-serif"],
        mono: ["Fira Code", "monospace"],
      },
    },
  },
  plugins: [],
}
