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

from .util import log

SITE = "https://zaiaku-zero-ikuji.pages.dev"
DEFAULT_TAGS = ["#育児", "#新米ママ", "#新米パパ", "#罪悪感ゼロ育児"]
_BASE = "https://graph.threads.net/v1.0"
_LIMIT = 480  # 公式上限500。余裕をみる


def _creds() -> dict | None:
    uid = (os.environ.get("THREADS_USER_ID") or "").strip()
    tok = (os.environ.get("THREADS_ACCESS_TOKEN") or "").strip()
    return {"user_id": uid, "token": tok} if uid and tok else None


def compose_post(meta: dict, slug: str, tags: list[str] | None = None) -> str:
    """記事メタから投稿本文を組み立てる（500字以内）。"""
    tagline = " ".join(tags or DEFAULT_TAGS)
    url = f"{SITE}/blog/{slug.lstrip('/')}"
    title = (meta.get("title") or "").strip()
    desc = (meta.get("description") or "").strip()

    def build(hook: str) -> str:
        parts = [title]
        if hook:
            parts.append(hook)
        parts += [url, tagline]
        return "\n\n".join(parts)

    hook = desc
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
