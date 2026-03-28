/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./app/**/*.{vue,ts,js}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Cascadia Code', 'monospace'],
      },
      colors: {
        surface: {
          950: '#08090c',
          900: '#0d1117',
          800: '#151b23',
          700: '#1c2333',
          600: '#252d3d',
          500: '#374151',
        },
        accent: { DEFAULT: '#d4a574', hover: '#c4915e', glow: 'rgba(212,165,116,0.25)' },
        ok: { DEFAULT: '#34d399' },
        danger: { DEFAULT: '#f87171' },
        warn: { DEFAULT: '#fbbf24' },
      },
    },
  },
}
