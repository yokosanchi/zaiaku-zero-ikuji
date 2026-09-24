"""新着記事を Threads（Meta）へ自動投稿する。

必要な環境変数（未設定なら投稿をスキップするだけ）:
    THREADS_USER_ID       … Threads のユーザーID（数値）
    THREADS_ACCESS_TOKEN  … 長期アクセストークン（約60日・要リフレッシュ）

Threads Graph API（https://graph.threads.net/v1.0）を使う。標準ライブラリのみ。
投稿は2段階: メディアコンテナ作成 → publish。
本文は最大500字。画像URL（記事のOGP）を付けると表示・到達が良くなる。
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

import re

from .util import CATEGORY_LABEL, log

SITE = "https://zaiaku-zero-ikuji.pages.dev"
BRAND_TAG = "#罪悪感ゼロ育児"
DEFAULT_TAGS = ["#育児", "#新米ママ", "#新米パパ", "#罪悪感ゼロ育児"]
_BASE = "https://graph.threads.net/v1.0"
_LIMIT = 480  # 公式上限500。余裕をみる


def _creds() -> dict | None:
    uid = (os.environ.get("THREADS_USER_ID") or "").strip()
    tok = (os.environ.get("THREADS_ACCESS_TOKEN") or "").strip()
    return {"user_id": uid, "token": tok} if uid and tok else None


def _hashtag_safe(s: str) -> str:
    """ハッシュタグに使えない区切り文字・空白を除去する。"""
    return re.sub(r"[・/／\s#]", "", s or "")


def _build_tags(meta: dict) -> list[str]:
    """カテゴリ＋記事タグから毎回変わるハッシュタグを組み立てる。
    ブランドタグ(#罪悪感ゼロ育児)は毎回固定で入れ、それ以外を記事内容に応じて変える
    （固定4つの繰り返しだと発見されにくく、フォロワーにも同じ投稿の繰り返しに見えるため）。
    Threadsはハッシュタグを大量に付けるほど伸びるわけではなく、むしろ多すぎると
    "いかにも自動投稿"に見えて逆効果になりやすいため、最大3つ（カテゴリ1＋記事タグ1＋ブランド）に絞る。"""
    out: list[str] = []
    cat_label = CATEGORY_LABEL.get(meta.get("category") or "", "")
    cat_tag = _hashtag_safe(cat_label)
    if cat_tag:
        out.append(f"#{cat_tag}")
    for t in meta.get("tags") or []:
        tag = _hashtag_safe(t)
        if tag and f"#{tag}" not in out and len(out) < 2:
            out.append(f"#{tag}")
    out.append(BRAND_TAG)
    return out


def compose_post(meta: dict, slug: str, tags: list[str] | None = None) -> str:
    """記事メタから投稿本文を組み立てる（500字以内）。"""
    tag_list = tags or _build_tags(meta) or DEFAULT_TAGS
    tagline = " ".join(tag_list)
    # Threads経由の流入を GA4 / Cloudflare Web Analytics で追えるようUTMを付与。
    # 末尾スラッシュ付きにして、Cloudflare Pages の /slug → /slug/ リダイレクトを挟まない
    # （リダイレクトを経由しないので UTM が確実にそのまま着地ページに届く）。
    url = f"{SITE}/blog/{slug.strip('/')}/?utm_source=threads&utm_medium=social&utm_campaign=auto_post"
    title = (meta.get("title") or "").strip()
    # thumbHookはサムネ用に設計済みの「読み手のペイン起点のキャッチ」。
    # SEO向けのdescriptionよりSNSの一文として自然なので優先する。
    hook_text = (meta.get("thumbHook") or meta.get("description") or "").strip()

    def build(hook: str) -> str:
        # 「タイトル→説明文→リンク→タグ」という並びは、いかにもRSS自動転載ボットの
        # テンプレに見えやすく、Threadsでは人間の投稿に比べて伸びにくい傾向がある。
        # ペイン起点の一文を最初に置いて共感で止めてから、タイトルとリンクをひとまとまりで
        # 添える方が、実際に人が書いた投稿に近い流れになる。
        parts = []
        if hook:
            parts.append(hook)
        title_and_url = f"{title}\n{url}" if title else url
        parts.append(title_and_url)
        parts.append(tagline)
        return "\n\n".join(parts)

    hook = hook_text
    text = build(hook)
    while hook and len(text) > _LIMIT:
        hook = hook[: max(1, len(hook) - 6)]
        text = build(hook.rstrip("、。・ ") + "…")
    if len(text) > _LIMIT:
        text = build("")
    return text


def _post_form(url: str, params: dict) -> dict:
    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={"User-Agent": "kzi-bot/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _get(url: str, params: dict) -> dict:
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{url}?{q}", headers={"User-Agent": "kzi-bot/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def refresh_token() -> str | None:
    """長期トークンを延長する（>24h経過が条件）。新トークンを返す。失敗で None。
    ※GitHub Secrets への書き戻しは自動化されない。戻り値をログに出すだけ。"""
    c = _creds()
    if not c:
        return None
    try:
        res = _get(
            f"{_BASE}/refresh_access_token",
            {"grant_type": "th_refresh_token", "access_token": c["token"]},
        )
        new = res.get("access_token")
        if new and new != c["token"]:
            log("  Threads: トークンをリフレッシュ（新トークンを Secret に反映してください）")
        return new
    except Exception as e:  # noqa: BLE001
        log(f"  Threads: トークンリフレッシュ不可（{e}）")
        return None


def post(text: str, image_url: str | None = None) -> str | None:
    """投稿する。成功で投稿ID、キー未設定や失敗で None。"""
    c = _creds()
    if not c:
        log("  Threads: キー未設定 → 投稿スキップ")
        return None

    params = {"access_token": c["token"], "text": text}
    if image_url:
        params["media_type"] = "IMAGE"
        params["image_url"] = image_url if image_url.startswith("http") else SITE + image_url
    else:
        params["media_type"] = "TEXT"

    try:
        created = _post_form(f"{_BASE}/{c['user_id']}/threads", params)
        cid = created.get("id")
        if not cid:
            log(f"  Threads: コンテナ作成に失敗 {json.dumps(created)[:200]}")
            return None
        published = _post_form(
            f"{_BASE}/{c['user_id']}/threads_publish",
            {"access_token": c["token"], "creation_id": cid},
        )
        pid = published.get("id")
        log(f"  Threads: 投稿しました id={pid}")
        return pid
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:400]
        log(f"  Threads: 投稿失敗 HTTP {e.code}: {detail}")
        return None
    except Exception as e:  # noqa: BLE001
        log(f"  Threads: 投稿失敗 {e}")
        return None
