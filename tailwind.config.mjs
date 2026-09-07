import typography from '@tailwindcss/typography';

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // 明るいポップ基調
        cream: '#FFF9F0',
        paper: '#FFFFFF',
        ink: '#3F3A4A',
        'ink-soft': '#7E7994',
        coral: { DEFAULT: '#FF7E6B', deep: '#F2624D', soft: '#FFE1DB' },
        sun: { DEFAULT: '#FFC24B', deep: '#F0A81F', soft: '#FFEFC9' },
        sky: { DEFAULT: '#5CC8E8', deep: '#2FA7CC', soft: '#D6F1FA' },
        mint: { DEFAULT: '#63D2A4', deep: '#3EB587', soft: '#D5F4E8' },
        grape: { DEFAULT: '#B49BE0', deep: '#9678CC', soft: '#EBE2FA' },
      },
      fontFamily: {
        heading: ['"Zen Maru Gothic"', 'ui-rounded', 'system-ui', 'sans-serif'],
        body: ['"Zen Kaku Gothic New"', 'system-ui', 'sans-serif'],
        hand: ['"Yomogi"', '"Zen Maru Gothic"', 'cursive'],
      },
      borderRadius: {
        blob: '42% 58% 63% 37% / 41% 44% 56% 59%',
      },
      boxShadow: {
        pop: '4px 4px 0 rgba(63, 58, 74, 0.12)',
        'pop-lg': '8px 8px 0 rgba(63, 58, 74, 0.12)',
        soft: '0 14px 34px -14px rgba(63, 58, 74, 0.28)',
      },
      keyframes: {
        floaty: {
          '0%,100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        wiggle: {
          '0%,100%': { transform: 'rotate(-4deg)' },
          '50%': { transform: 'rotate(4deg)' },
        },
      },
      animation: {
        floaty: 'floaty 6s ease-in-out infinite',
        wiggle: 'wiggle 2.6s ease-in-out infinite',
      },
      typography: (theme) => ({
        DEFAULT: {
          css: {
            '--tw-prose-body': theme('colors.ink'),
            '--tw-prose-headings': theme('colors.ink'),
            '--tw-prose-links': theme('colors.coral.deep'),
            '--tw-prose-bold': theme('colors.ink'),
            '--tw-prose-counters': theme('colors.coral.deep'),
            '--tw-prose-bullets': theme('colors.coral.DEFAULT'),
            '--tw-prose-quotes': theme('colors.ink'),
            '--tw-prose-quote-borders': theme('colors.sky.DEFAULT'),
            '--tw-prose-hr': theme('colors.coral.soft'),
            maxWidth: '70ch',
            // ファクトボックスの引用符を消す
            'blockquote p:first-of-type::before': { content: 'none' },
            'blockquote p:last-of-type::after': { content: 'none' },
          },
        },
      }),
    },
  },
  plugins: [typography],
};
