/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      // National-parks earth-tone palette.
      // - forest: primary brand green
      // - bark:   brown, for optional earthy accents
      // - sand:   beige/tan, used for page backgrounds and soft fills
      // - clay:   terracotta, used for destructive/warning actions
      // Neutrals use Tailwind's built-in warm "stone" scale for text/borders.
      colors: {
        forest: {
          50: '#f2f7f2',
          100: '#dfece1',
          200: '#bfd8c4',
          300: '#93bb9c',
          400: '#629874',
          500: '#427a56',
          600: '#316043',
          700: '#284d37',
          800: '#223f2e',
          900: '#1d3427',
        },
        bark: {
          50: '#f7f3ee',
          100: '#ebe0d3',
          200: '#d8c3a9',
          300: '#c0a079',
          400: '#a87f53',
          500: '#8e6740',
          600: '#745234',
          700: '#5c422b',
          800: '#493623',
          900: '#3a2b1d',
        },
        sand: {
          50: '#faf6ee',
          100: '#f2e9d8',
          200: '#e6d7bd',
          300: '#d5bf98',
          400: '#c1a273',
          500: '#a8875a',
          600: '#8b6d47',
          700: '#6d5639',
          800: '#4f3f2b',
          900: '#3b2f21',
        },
        clay: {
          50: '#fbefe9',
          100: '#f5d9cb',
          200: '#e9b39a',
          300: '#db8b68',
          400: '#cc6941',
          500: '#b1512c',
          600: '#954324',
          700: '#75351f',
          800: '#5a2a1b',
          900: '#4a2417',
        },
      },
    },
  },
  plugins: [],
}
