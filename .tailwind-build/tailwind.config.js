module.exports = {
  content: ['../resume-maker.html'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        ink: '#101828',
        mist: '#F8FAFC',
        line: '#E5E7EB',
        brand: {
          50: '#eef4ff',
          100: '#dfeaff',
          200: '#c7dbff',
          300: '#a4c3ff',
          400: '#7ca1ff',
          500: '#4f7bff',
          600: '#345de6',
          700: '#2949b4',
          800: '#243e8e',
          900: '#23376f',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Space Grotesk', 'Inter', 'system-ui', 'sans-serif'],
        hindi: ['Noto Sans Devanagari', 'Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        soft: '0 10px 30px rgba(15, 23, 42, 0.08)',
        card: '0 16px 40px rgba(2, 6, 23, 0.08)',
      },
      keyframes: {
        pulseSoft: {
          '0%, 100%': { transform: 'scale(1)', opacity: '1' },
          '50%': { transform: 'scale(1.02)', opacity: '.92' },
        },
      },
      animation: {
        pulseSoft: 'pulseSoft 1.8s ease-in-out infinite',
      },
    },
  },
  plugins: [],
};
