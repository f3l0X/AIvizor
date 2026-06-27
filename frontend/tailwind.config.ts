import type { Config } from 'tailwindcss';

const config: Config = {
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
