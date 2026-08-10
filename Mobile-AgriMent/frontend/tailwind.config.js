/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#2E7D32",
          light: "#4CAF50",
          dark: "#1B5E20",
        },
        secondary: {
          DEFAULT: "#4CAF50",
          light: "#81C784",
          dark: "#388E3C",
        },
        background: "#F8F9FA",
        surface: "#FFFFFF",
        text: {
          DEFAULT: "#212121",
          secondary: "#757575",
        },
        danger: "#D32F2F",
        warning: "#FF9800",
        success: "#4CAF50",
        info: "#2196F3",
      },
      borderRadius: {
        xl: "16px",
        "2xl": "20px",
        "3xl": "24px",
      },
      boxShadow: {
        card: "0 2px 12px rgba(0,0,0,0.08)",
        elevated: "0 4px 20px rgba(0,0,0,0.12)",
      },
    },
  },
  plugins: [],
};
