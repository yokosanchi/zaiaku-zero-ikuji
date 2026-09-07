/**
 * きょうの訪問者カウンタ（Cloudflare Pages Functions + KV）。
 *
 * セットアップ（1回だけ、Cloudflare ダッシュボード）:
 *   1. Workers & Pages → KV → 名前空間を作成（例: kzi-hits）
 *   2. 対象の Pages プロジェクト → Settings → Functions → KV namespace bindings
 *      Variable name: HITS  /  KV namespace: 作成したもの
 *
 * 未設定でも 200 を返す（フロントはカウンタ表示を出さないだけ）。
 * 日次キーは 3 日で自動失効。1 訪問者につき 1 日 1 回だけ加算（フロントが localStorage で制御）。
 */
export async function onRequest(context) {
  const { request, env } = context;
  const kv = env.HITS;
  const headers = { "content-type": "application/json", "cache-control": "no-store" };

  const day = new Date().toISOString().slice(0, 10); // UTC 日付
  const dayKey = `d:${day}`;
  const totalKey = "t:all";

  if (!kv) {
    return new Response(JSON.stringify({ error: "kv-unbound", day }), { headers });
  }

  const url = new URL(request.url);
  const bump = request.method === "POST" || url.searchParams.get("bump") === "1";

  let today = parseInt((await kv.get(dayKey)) || "0", 10) || 0;
  let total = parseInt((await kv.get(totalKey)) || "0", 10) || 0;

  if (bump) {
    today += 1;
    total += 1;
    context.waitUntil(
      Promise.all([
        kv.put(dayKey, String(today), { expirationTtl: 60 * 60 * 24 * 3 }),
        kv.put(totalKey, String(total)),
      ])
    );
  }

  return new Response(JSON.stringify({ today, total, day }), { headers });
}
