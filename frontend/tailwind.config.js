/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        paytm: {
          navy: '#002970',
          navyDark: '#001D52',
          cyan: '#00BAF2',
          bg: '#F5F7FA',
          border: '#E5E9F0',
        },
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', '"Noto Sans Devanagari"', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
