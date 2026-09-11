import { getCollection } from 'astro:content';
import { CATEGORIES, STAGES } from '../lib/site';

// @astrojs/sitemap はこの環境でビルドが落ちるため使わない（CLAUDE.md 参照）。
// 代わりに手書きの XML エンドポイントで最小限の sitemap を出す。
export async function GET({ site }) {
  const base = site?.origin ?? 'https://zaiaku-zero-ikuji.pages.dev';
  const posts = (await getCollection('blog', ({ data }) => !data.draft)).sort(
    (a, b) => b.data.pubDate.valueOf() - a.data.pubDate.valueOf()
  );

  const staticUrls = ['/', '/about/', '/blog/', '/categories/', '/stages/'];
  const catUrls = CATEGORIES.map((c) => `/categories/${c.key}/`);
  const stageUrls = STAGES.map((s) => `/stages/${s.key}/`);

  const urlTag = (loc, lastmod, priority) =>
    `  <url><loc>${base}${loc}</loc>` +
    (lastmod ? `<lastmod>${lastmod}</lastmod>` : '') +
    `<priority>${priority}</priority></url>`;

  const body =
    `<?xml version="1.0" encoding="UTF-8"?>\n` +
    `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n` +
    staticUrls.map((u) => urlTag(u, undefined, u === '/' ? '1.0' : '0.7')).join('\n') +
    '\n' +
    catUrls.map((u) => urlTag(u, undefined, '0.6')).join('\n') +
    '\n' +
    stageUrls.map((u) => urlTag(u, undefined, '0.6')).join('\n') +
    '\n' +
    posts
      .map((p) =>
        urlTag(
          `/blog/${p.slug}/`,
          (p.data.updatedDate ?? p.data.pubDate).toISOString().slice(0, 10),
          '0.8'
        )
      )
      .join('\n') +
    '\n</urlset>\n';

  return new Response(body, {
    headers: { 'Content-Type': 'application/xml; charset=utf-8' },
  });
}
