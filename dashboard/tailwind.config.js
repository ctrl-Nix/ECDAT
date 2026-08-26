/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#0b0f19',
        'accent-blue': '#60a5fa',
      },
      boxShadow: {
        glow: '0 0 80px rgba(96, 165, 250, 0.08)',
      },
    },
  },
  plugins: [],
}
