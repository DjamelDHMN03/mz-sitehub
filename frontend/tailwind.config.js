/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class", '[data-theme="dark"]'],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        mz: {
          primary: "var(--mz-primary)",
          "primary-hover": "var(--mz-primary-hover)",
          "primary-active": "var(--mz-primary-active)",
          secondary: "var(--mz-secondary)",
          accent: "var(--mz-accent)",
          ooredoo: "var(--mz-ooredoo-red)",
          background: "var(--mz-background)",
          surface: "var(--mz-surface)",
          "surface-2": "var(--mz-surface-2)",
          card: "var(--mz-card)",
          modal: "var(--mz-modal)",
          input: "var(--mz-input)",
          border: "var(--mz-border)",
          "border-strong": "var(--mz-border-strong)",
          text: "var(--mz-text)",
          "text-muted": "var(--mz-text-muted)",
          "text-disabled": "var(--mz-text-disabled)",
          success: "var(--mz-success)",
          warning: "var(--mz-warning)",
          danger: "var(--mz-danger)",
          info: "var(--mz-info)",
        },
        "mz-status": {
          operationnel: "var(--mz-status-operationnel)",
          "en-cours": "var(--mz-status-en-cours)",
          attente: "var(--mz-status-attente)",
          bloque: "var(--mz-status-bloque)",
          refuse: "var(--mz-status-refuse)",
          nouveau: "var(--mz-status-nouveau)",
        },
      },
      borderRadius: {
        "mz-sm": "var(--mz-radius-sm)",
        "mz-md": "var(--mz-radius-md)",
        "mz-lg": "var(--mz-radius-lg)",
      },
      boxShadow: {
        "mz-1": "var(--mz-shadow-1)",
        "mz-2": "var(--mz-shadow-2)",
      },
    },
  },
  plugins: [],
};
