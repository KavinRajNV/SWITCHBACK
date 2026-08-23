/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        forest: {
          light: '#298A64',
          DEFAULT: '#1F6B4D',
          dark: '#18543C',
          deep: '#0F3827',
        },
        amber: {
          light: '#F4AA5B',
          DEFAULT: '#E08A34',
          dark: '#C77524',
        },
        paper: {
          light: '#FFFFFF',
          DEFAULT: '#FAF7F0',
          dark: '#F4EFE3',
        },
        contour: {
          DEFAULT: '#E4DFD3',
          dark: '#D5CDBC',
        },
        ink: {
          DEFAULT: '#1C2421',
          light: '#2F3D37',
        },
        muted: {
          DEFAULT: '#4A5852',
          light: '#6C7E76',
        }
      },
      fontFamily: {
        heading: ['"Space Grotesk"', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
