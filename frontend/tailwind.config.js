/** @type {import('tailwindcss').Config} */
export default {
    content: [
      "./index.html",
      "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
      extend: {
        colors: {
          blue: {
            500: '#7e69b3',
            600: '#6c579e', // dominant
          },
          indigo: {
            300: '#beb2db',
            400: '#8c77be',
            500: '#6c579e', // dominant
            600: '#5a458c',
            950: '#231b37',
          }
        }
      },
    },
    plugins: [],
  }