/**
 * お問い合わせフォームの送信を受け取り、Resend経由でメール通知する
 * （Cloudflare Pages Functions）。
 *
 * セットアップ（1回だけ、Cloudflareダッシュボード）:
 *   1. https://resend.com で無料アカウントを作成し、APIキーを発行
 *   2. Pages プロジェクト → Settings → Environment variables に以下を追加
 *      - RESEND_API_KEY   … Resendで発行したAPIキー（Secret推奨）
 *      - CONTACT_TO_EMAIL … 通知を受け取りたい実際のメールアドレス（サイト上には非公開）
 *
 * ドメイン未設定でも、Resendの共有送信元(onboarding@resend.dev)から
 * アカウント登録済みのメールアドレス宛には送信できる。
 *
 * 未設定でも 500 系にはせず、フロント側にエラーとして伝える（フォーム自体は壊さない）。
 * 簡易スパム対策: ハニーポット欄 + 送信の速すぎるボット的挙動を弾く。
 */
export async function onRequestPost(context) {
  const { request, env } = context;
  const headers = { "content-type": "application/json", "cache-control": "no-store" };

  let body;
  try {
    body = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: "invalid-body" }), { status: 400, headers });
  }

  const name = String(body.name || "").trim().slice(0, 100) || "匿名";
  const email = String(body.email || "").trim().slice(0, 200);
  const category = String(body.category || "").trim().slice(0, 50);
  const message = String(body.message || "").trim().slice(0, 3000);
  const honeypot = String(body.website || "").trim();
  const startedAt = Number(body.startedAt) || 0;

  // ハニーポット欄が埋まっている、または表示から3秒未満での送信はボットとみなして静かに成功扱いにする
  // （送信者に「弾かれた」と悟らせない一般的な手法）
  if (honeypot || (startedAt && Date.now() - startedAt < 3000)) {
    return new Response(JSON.stringify({ ok: true }), { headers });
  }

  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return new Response(JSON.stringify({ error: "invalid-email" }), { status: 400, headers });
  }
  if (!message) {
    return new Response(JSON.stringify({ error: "empty-message" }), { status: 400, headers });
  }

  const apiKey = env.RESEND_API_KEY;
  const toEmail = env.CONTACT_TO_EMAIL;
  if (!apiKey || !toEmail) {
    return new Response(JSON.stringify({ error: "not-configured" }), { status: 503, headers });
  }

  const subject = `[罪悪感ゼロ育児] お問い合わせ${category ? `（${category}）` : ""}`;
  const text =
    `お名前: ${name}\n` +
    `返信先: ${email}\n` +
    `カテゴリ: ${category || "（未選択）"}\n\n` +
    `----- 本文 -----\n${message}\n`;

  try {
    const resp = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: "罪悪感ゼロ育児 お問い合わせ <onboarding@resend.dev>",
        to: [toEmail],
        reply_to: email,
        subject,
        text,
      }),
    });
    if (!resp.ok) {
      const detail = await resp.text();
      return new Response(JSON.stringify({ error: "send-failed", detail: detail.slice(0, 300) }), {
        status: 502,
        headers,
      });
    }
  } catch (e) {
    return new Response(JSON.stringify({ error: "send-failed", detail: String(e).slice(0, 300) }), {
      status: 502,
      headers,
    });
  }

  return new Response(JSON.stringify({ ok: true }), { headers });
}
