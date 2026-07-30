/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cat: {
          yellow: "#FFCD00",
          yellowHover: "#E5B800",
          dark: "#0F1115",
          card: "#171A21",
          cardHover: "#1F242E",
          border: "#282E3D",
          steel: "#242936",
          subtext: "#9CA3AF",
          accent: "#F59E0B"
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace']
      }
    },
  },
  plugins: [],
}
