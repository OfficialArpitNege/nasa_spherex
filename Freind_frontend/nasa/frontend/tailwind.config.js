/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cyan: {
          400: '#67e8f9',
          500: '#22d3ee',
        },
        orange: {
          500: '#ff7a3d',
        }
      }
    },
  },
  plugins: [],
}
