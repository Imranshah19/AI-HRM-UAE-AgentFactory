const path = require("path");
const { fontFamily } = require("tailwindcss/defaultTheme");

/** @type {import('tailwindcss').Config} */
const config = {
  darkMode: ["class"],

  // Use __dirname so paths are always relative to this config file (/app/frontend/),
  // regardless of the process.cwd() when `next dev frontend` runs from /app.
  content: [
    path.join(__dirname, "./pages/**/*.{js,ts,jsx,tsx,mdx}"),
    path.join(__dirname, "./components/**/*.{js,ts,jsx,tsx,mdx}"),
    path.join(__dirname, "./app/**/*.{js,ts,jsx,tsx,mdx}"),
    path.join(__dirname, "./src/**/*.{js,ts,jsx,tsx,mdx}"),
  ],

  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },

    extend: {
      colors: {
        border:      "hsl(var(--border))",
        input:       "hsl(var(--input))",
        ring:        "hsl(var(--ring))",
        background:  "hsl(var(--background))",
        foreground:  "hsl(var(--foreground))",

        primary: {
          DEFAULT:    "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT:    "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT:    "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT:    "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT:    "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT:    "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT:    "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },

        hrms: {
          50:  "#eff6ff",
          100: "#dbeafe",
          200: "#bfdbfe",
          300: "#93c5fd",
          400: "#60a5fa",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
          800: "#1e40af",
          900: "#1e3a8a",
          950: "#172554",
        },

        status: {
          active:     "#22c55e",
          inactive:   "#94a3b8",
          pending:    "#f59e0b",
          approved:   "#10b981",
          rejected:   "#ef4444",
          onleave:    "#8b5cf6",
          probation:  "#f97316",
        },
      },

      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },

      fontFamily: {
        sans: ["var(--font-inter)", ...fontFamily.sans],
        mono: ["var(--font-geist-mono)", ...fontFamily.mono],
      },

      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to:   { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to:   { height: "0" },
        },
        "slide-in-from-top": {
          from: { transform: "translateY(-100%)" },
          to:   { transform: "translateY(0)" },
        },
        "fade-in": {
          from: { opacity: "0" },
          to:   { opacity: "1" },
        },
        "zoom-in-95": {
          from: { opacity: "0", transform: "scale(0.95)" },
          to:   { opacity: "1", transform: "scale(1)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up":   "accordion-up 0.2s ease-out",
        "fade-in":        "fade-in 0.15s ease-out",
        "zoom-in-95":     "zoom-in-95 0.2s ease-out",
      },

      spacing: {
        "18": "4.5rem",
        "88": "22rem",
        "128": "32rem",
      },

      boxShadow: {
        card:         "0 1px 3px 0 rgb(0 0 0 / 0.07), 0 1px 2px -1px rgb(0 0 0 / 0.07)",
        "card-hover": "0 4px 6px -1px rgb(0 0 0 / 0.08), 0 2px 4px -2px rgb(0 0 0 / 0.08)",
        modal:        "0 20px 60px -10px rgb(0 0 0 / 0.3)",
      },
    },
  },

  plugins: [
    require("tailwindcss-animate"),
  ],
};

module.exports = config;
