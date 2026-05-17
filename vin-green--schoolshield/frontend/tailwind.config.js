/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#030604',
          900: '#060c07',
          800: '#0a1409',
          700: '#0f1e0e',
          600: '#162814',
        },
      },
      fontFamily: {
        display: ['"Be Vietnam Pro"', 'sans-serif'],
        sans:    ['"DM Sans"', 'sans-serif'],
        mono:    ['"JetBrains Mono"', 'monospace'],
      },
      keyframes: {
        breathe: {
          '0%, 100%': { opacity: '0.6', transform: 'scale(1)' },
          '50%':       { opacity: '1',   transform: 'scale(1.04)' },
        },
        tickIn: {
          '0%':   { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        breathe: 'breathe 3s ease-in-out infinite',
        tickIn:  'tickIn 0.4s ease-out forwards',
      },
    },
  },
  plugins: [],
}
