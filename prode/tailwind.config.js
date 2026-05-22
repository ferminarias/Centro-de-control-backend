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
          base: '#000000',
          surface: '#0D0D0D',
          elevated: '#181818',
          overlay: '#222222',
        },
        border: {
          DEFAULT: '#2A2A2A',
          subtle: '#1A1A1A',
          strong: '#404040',
        },
        content: {
          primary: '#FFFFFF',
          secondary: '#8C8C8C',
          muted: '#4A4A4A',
          inverse: '#000000',
        },
        accent: {
          DEFAULT: '#1946E3',
          hover: '#1538C4',
          subtle: 'rgba(25, 70, 227, 0.10)',
          border: 'rgba(25, 70, 227, 0.30)',
        },
        status: {
          win: '#22C55E',
          loss: '#EF4444',
          draw: '#F59E0B',
          pending: '#6B6B6B',
        },
      },
      backgroundImage: {
        'nods-gradient': 'linear-gradient(135deg, #000000 0%, #0D0D0D 100%)',
        'accent-glow': 'radial-gradient(ellipse at 50% 0%, rgba(25,70,227,0.20) 0%, transparent 65%)',
      },
      boxShadow: {
        card: '0 1px 3px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.05)',
        'card-hover': '0 4px 20px rgba(0,0,0,0.7), 0 0 0 1px rgba(255,255,255,0.08)',
        'accent': '0 0 24px rgba(25, 70, 227, 0.25)',
        'input-focus': '0 0 0 2px rgba(25, 70, 227, 0.30)',
      },
      animation: {
        'fade-in': 'fadeIn 0.35s ease-out',
        'slide-up': 'slideUp 0.35s ease-out',
        'pulse-soft': 'pulseSoft 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
      },
    },
  },
  plugins: [],
}
