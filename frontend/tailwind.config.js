/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: "#002F6C",
          50: "#F0F4FA",
          100: "#D5E0EF",
          600: "#002F6C",
          700: "#00255A",
        },
        muted: "#5A6570",
        surface: "#F5F7F9",
        border: "#E1E5EA",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "Helvetica", "Arial", "sans-serif"],
      },
      borderRadius: { DEFAULT: "12px", sm: "8px", lg: "16px" },
      boxShadow: {
        card: "0 1px 3px rgba(0,47,108,0.08), 0 4px 12px rgba(0,47,108,0.05)",
      },
    },
  },
  plugins: [],
};
