/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        mori: ['PP Mori', 'sans-serif'],
      },
      colors: {
        bg: {
          base: '#0A0A0A',
          surface: '#111111',
          elevated: '#1A1A1A',
          overlay: '#222222',
        },
        border: {
          DEFAULT: '#282828',
          subtle: '#1E1E1E',
          strong: '#3A3A3A',
        },
        content: {
          primary: '#F5F5F5',
          secondary: '#8B8B8B',
          muted: '#4A4A4A',
          inverse: '#0A0A0A',
        },
        accent: {
          DEFAULT: '#4ADE80',
          hover: '#22C55E',
          subtle: 'rgba(74, 222, 128, 0.08)',
          border: 'rgba(74, 222, 128, 0.2)',
        },
        status: {
          win: '#4ADE80',
          loss: '#F87171',
          draw: '#FBBF24',
          pending: '#8B8B8B',
        },
      },
      backgroundImage: {
        'nods-gradient': 'linear-gradient(135deg, #0A0A0A 0%, #111111 100%)',
        'accent-glow': 'radial-gradient(ellipse at center, rgba(74,222,128,0.15) 0%, transparent 70%)',
      },
      boxShadow: {
        'card': '0 1px 3px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.04)',
        'card-hover': '0 4px 16px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.08)',
        'accent': '0 0 20px rgba(74, 222, 128, 0.15)',
        'input-focus': '0 0 0 2px rgba(74, 222, 128, 0.25)',
      },
      animation: {
        'fade-in': 'fadeIn 0.4s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'pulse-soft': 'pulseSoft 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        },
      },
    },
  },
  plugins: [],
}
