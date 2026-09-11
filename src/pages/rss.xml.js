import { getCollection } from 'astro:content';

// 手書きの RSS 2.0（依存追加なし）。更新頻度の証明＝E-E-A-T/クロール促進のため。
function esc(s) {
  return String(s ?? '').replace(/[<>&'"]/g, (c) => ({
    '<': '&lt;', '>': '&gt;', '&': '&amp;', "'": '&apos;', '"': '&quot;',
  }[c]));
}

export async function GET({ site }) {
  const base = site?.origin ?? 'https://zaiaku-zero-ikuji.pages.dev';
  const posts = (await getCollection('blog', ({ data }) => !data.draft))
    .sort((a, b) => b.data.pubDate.valueOf() - a.data.pubDate.valueOf())
    .slice(0, 40);

  const items = posts
    .map((p) => {
      const url = `${base}/blog/${p.slug}/`;
      const date = (p.data.updatedDate ?? p.data.pubDate).toUTCString();
      return (
        `  <item>\n` +
        `    <title>${esc(p.data.title)}</title>\n` +
        `    <link>${url}</link>\n` +
        `    <guid isPermaLink="true">${url}</guid>\n` +
        `    <pubDate>${date}</pubDate>\n` +
        `    <description>${esc(p.data.description)}</description>\n` +
        `  </item>`
      );
    })
    .join('\n');

  const body =
    `<?xml version="1.0" encoding="UTF-8"?>\n` +
    `<rss version="2.0"><channel>\n` +
    `  <title>罪悪感ゼロ育児</title>\n` +
    `  <link>${base}/</link>\n` +
    `  <description>「手抜き」じゃなく「心を守る選択」。新米パパママのための育児メディア。</description>\n` +
    `  <language>ja</language>\n` +
    `${items}\n` +
    `</channel></rss>\n`;

  return new Response(body, {
    headers: { 'Content-Type': 'application/xml; charset=utf-8' },
  });
}
