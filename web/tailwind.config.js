/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1c1612",
        "ink-soft": "#5c5148",
        paper: "#f3eee6",
        cream: "#fffaf3",
        copper: "#c4622d",
        "copper-deep": "#8d3e14",
        ok: "#0d7a45",
        "ok-soft": "#e7f6ee",
        defect: "#d61f3a",
        "defect-soft": "#fde8eb",
      },
      fontFamily: {
        sans: ["Outfit", "system-ui", "sans-serif"],
        display: ["Fraunces", "Georgia", "serif"],
      },
      boxShadow: {
        card: "0 24px 60px -28px rgba(28, 22, 18, 0.45)",
        stamp: "0 16px 40px -18px rgba(28, 22, 18, 0.35)",
      },
    },
  },
  plugins: [],
}
