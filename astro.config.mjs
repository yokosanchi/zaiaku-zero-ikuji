import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';
import mdx from '@astrojs/mdx';

// 本番 URL（Cloudflare Pages）。独自ドメイン取得後に差し替える。
export default defineConfig({
  site: 'https://zaiaku-zero-ikuji.pages.dev',
  integrations: [tailwind(), mdx()],
});
