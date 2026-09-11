/**
 * アフィリエイトCTAのクリック計測（Cloudflare Pages Functions + KV）。
 *
 * A8.net 側の成果承認には数日〜1か月のラグがあるため、
 * 「どの提携先・どの記事がクリックされているか」を自前で即時に見えるようにする。
 * 成果（購入等）自体はA8側でしか分からない。ここは導線のクリック数だけ。
 *
 * セットアップ: hits.js と同じ KV 名前空間（HITS）を共有する。
 * 未バインドでも 204 を返すだけで、記事の閲覧は一切妨げない。
 *
 * 使い方（AffiliateCTA.astro から）:
 *   navigator.sendBeacon('/api/aff-click?key=carryon&slug=kodomofuku-kaitashi-yameru')
 *
 * 集計の読み方（Cloudflare ダッシュボード → Workers & Pages → KV → 該当キーを確認）:
 *   aff:<key>:total          … その提携先の累計クリック
 *   aff:<key>:d:<YYYY-MM-DD> … 日別（30日で失効）
 *   affslug:<slug>:total     … その記事からのクリック累計
 */
export async function onRequest(context) {
  const { request, env } = context;
  const kv = env.HITS;
  const headers = { "content-type": "application/json", "cache-control": "no-store" };

  if (request.method !== "POST") {
    return new Response(null, { status: 204, headers });
  }
  if (!kv) {
    return new Response(JSON.stringify({ error: "kv-unbound" }), { status: 200, headers });
  }

  const url = new URL(request.url);
  const key = (url.searchParams.get("key") || "").replace(/[^a-z0-9_-]/gi, "").slice(0, 40);
  const slug = (url.searchParams.get("slug") || "").replace(/[^a-z0-9_-]/gi, "").slice(0, 80);
  if (!key) {
    return new Response(JSON.stringify({ error: "no-key" }), { status: 200, headers });
  }

  const day = new Date().toISOString().slice(0, 10);
  const totalKey = `aff:${key}:total`;
  const dayKey = `aff:${key}:d:${day}`;
  const slugKey = slug ? `affslug:${slug}:total` : null;

  const bump = async (k, ttl) => {
    const cur = parseInt((await kv.get(k)) || "0", 10) || 0;
    await kv.put(k, String(cur + 1), ttl ? { expirationTtl: ttl } : undefined);
  };

  context.waitUntil(
    Promise.all([
      bump(totalKey),
      bump(dayKey, 60 * 60 * 24 * 30),
      slugKey ? bump(slugKey) : Promise.resolve(),
    ])
  );

  return new Response(JSON.stringify({ ok: true }), { headers });
}
