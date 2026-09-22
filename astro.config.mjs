import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';
import mdx from '@astrojs/mdx';

// 本番 URL（Cloudflare Pages）。独自ドメイン取得後に差し替える。
export default defineConfig({
  site: 'https://zaiaku-zero-ikuji.pages.dev',
  integrations: [tailwind(), mdx()],
  vite: {
    build: {
      // /pagefind/pagefind.js は npm run build の postbuild(pagefind CLI)が
      // dist/pagefind/ に生成する実行時専用ファイルで、ソースツリーには存在しない。
      // Rollup にバンドル解決させず、ブラウザ上のfetchに任せる。
      rollupOptions: { external: ['/pagefind/pagefind.js'] },
    },
  },
});
