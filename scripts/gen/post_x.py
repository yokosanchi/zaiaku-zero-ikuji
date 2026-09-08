"""新着記事を X（Twitter）へ自動投稿する。

必要な環境変数（未設定なら投稿をスキップするだけ）:
    X_API_KEY / X_API_SECRET          … App の API Key / Secret（Consumer key）
    X_ACCESS_TOKEN / X_ACCESS_SECRET  … ユーザーの Access Token / Secret

X API v2 の POST /2/tweets を OAuth 1.0a（HMAC-SHA1）で叩く。追加依存なし（標準ライブラリのみ）。
App の権限は "Read and write" が必要。権限変更後は Access Token を作り直すこと。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request

from .util import log

SITE = "https://zaiaku-zero-ikuji.pages.dev"
DEFAULT_TAGS = ["#育児", "#新米ママ", "#新米パパ", "#罪悪感ゼロ育児"]
_ENDPOINT = "https://api.twitter.com/2/tweets"
_LIMIT = 275  # X は 280。少し余裕をみる
_URL_WEIGHT = 23  # t.co 短縮後の固定長


def _pct(s: object) -> str:
    return urllib.parse.quote(str(s), safe="~")


def _creds() -> dict | None:
    keys = ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")
    vals = {k: (os.environ.get(k) or "").strip() for k in keys}
    return vals if all(vals.values()) else None


def _weight(text: str) -> int:
    w = 0
    for ch in text:
        o = ord(ch)
        wide = (
            0x1100 <= o <= 0x115F
            or 0x2600 <= o <= 0x27BF
            or 0x2E80 <= o <= 0x303E
            or 0x3041 <= o <= 0x33FF
            or 0x3400 <= o <= 0x4DBF
            or 0x4E00 <= o <= 0x9FFF
            or 0xA000 <= o <= 0xA4CF
            or 0xF900 <= o <= 0xFAFF
            or 0xFE30 <= o <= 0xFE4F
            or 0xFF00 <= o <= 0xFF60
            or 0xFFE0 <= o <= 0xFFE6
            or 0x1F000 <= o <= 0x1FAFF
            or 0x20000 <= o <= 0x3FFFD
        )
        w += 2 if wide else 1
    return w


def compose_tweet(meta: dict, slug: str, tags: list[str] | None = None) -> str:
    """記事メタからツイート本文を組み立てる（275字重み以内）。"""
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

    def over(text: str) -> bool:
        # url を固定長として数える
        return _weight(text.replace(url, "u" * _URL_WEIGHT)) > _LIMIT

    hook = desc
    text = build(hook)
    while hook and over(text):
        hook = hook[: max(1, len(hook) - 4)]
        text = build(hook.rstrip("、。・ ") + "…")
    if over(text):
        text = build("")  # タイトルだけでも溢れるなら hook を捨てる
    return text


def _auth_header(method: str, url: str, c: dict) -> str:
    oauth = {
        "oauth_consumer_key": c["X_API_KEY"],
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": c["X_ACCESS_TOKEN"],
        "oauth_version": "1.0",
    }
    param_str = "&".join(f"{_pct(k)}={_pct(v)}" for k, v in sorted(oauth.items()))
    base = "&".join([method.upper(), _pct(url), _pct(param_str)])
    signing_key = f"{_pct(c['X_API_SECRET'])}&{_pct(c['X_ACCESS_SECRET'])}"
    oauth["oauth_signature"] = base64.b64encode(
        hmac.new(signing_key.encode(), base.encode(), hashlib.sha1).digest()
    ).decode()
    return "OAuth " + ", ".join(f'{_pct(k)}="{_pct(v)}"' for k, v in sorted(oauth.items()))


def post_tweet(text: str) -> str | None:
    """投稿する。成功でツイートID、キー未設定や失敗で None。"""
    c = _creds()
    if not c:
        log("  X: キー未設定 → 投稿スキップ")
        return None

    body = json.dumps({"text": text}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        _ENDPOINT,
        data=body,
        method="POST",
        headers={
            "Authorization": _auth_header("POST", _ENDPOINT, c),
            "Content-Type": "application/json",
            "User-Agent": "kzi-bot/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
        tid = ((data.get("data") or {}).get("id"))
        log(f"  X: 投稿しました id={tid}")
        return tid
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:400]
        log(f"  X: 投稿失敗 HTTP {e.code}: {detail}")
        return None
    except Exception as e:  # noqa: BLE001
        log(f"  X: 投稿失敗 {e}")
        return None
