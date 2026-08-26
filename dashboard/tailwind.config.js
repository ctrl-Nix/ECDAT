/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'Segoe UI', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      colors: {
        // Mapped directly to CSS variables for dynamic theming / consistency
        void: 'var(--void)',
        surface: 'var(--surface)',
        'surface-r': 'var(--surface-r)',
        'surface-h': 'var(--surface-h)',
        border: 'var(--border)',
        'border-s': 'var(--border-s)',
        
        cyan: 'var(--cyan)',
        'cyan-10': 'var(--cyan-10)',
        'cyan-20': 'var(--cyan-20)',
        
        purple: 'var(--purple)',
        'purple-10': 'var(--purple-10)',
        
        green: 'var(--green)',
        'green-10': 'var(--green-10)',
        
        critical: 'var(--critical)',
        high: 'var(--high)',
        medium: 'var(--medium)',
        low: 'var(--low)',
        
        t1: 'var(--t1)',
        t2: 'var(--t2)',
        t3: 'var(--t3)',
        t4: 'var(--t4)',
      },
    },
  },
  plugins: [],
};
