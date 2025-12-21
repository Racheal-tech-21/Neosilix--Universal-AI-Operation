import tailwindAnimate from "tailwindcss-animate";

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  safelist: [
    'blur-[128px]',
    'blur-3xl',
    'blur-2xl',
  ],
  theme: {
    extend: {
      colors: {
        border: '#E5E7EB',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: '#7C3AED',
          light: '#C4B5FD',
          dark: '#4C1D95',
        },
        silver: {
          DEFAULT: '#C0C0C0',
          light: '#E5E5E5',
          dark: '#A9A9A9',
        },
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'pulse-fast': 'pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fadeIn': 'fadeIn 0.5s ease-in-out',
        'spin': 'spin 1s linear infinite',
        'float': 'float 3s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: 0, transform: 'translateY(-10px)' },
          '100%': { opacity: 1, transform: 'translateY(0)' },
        },
        float: {
          '0%, 100%': { transform: 'translate(-50%, -50%) translateY(0)' },
          '50%': { transform: 'translate(-50%, -50%) translateY(-10px)' },
        }
      },
      backdropBlur: {
        xs: '2px',
      }
    },
  },
  plugins: [tailwindAnimate],
}
