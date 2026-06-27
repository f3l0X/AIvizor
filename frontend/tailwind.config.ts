import type { Config } from 'tailwindcss';

const config: Config = {
  // Tema controlado por la clase `dark` en <html> (toggle manual), no por la
  // media query del SO. El script anti-FOUC del layout pone la clase inicial.
  darkMode: 'class',
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: '#3b82f6',
          dark: '#1d4ed8',
        },
      },
    },
  },
  plugins: [],
};

export default config;
