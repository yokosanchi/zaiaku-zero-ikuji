from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request

from .util import log

# 既定モデル。変えたい場合は GitHub の
# Settings → Secrets and variables → Actions → Variables に GEMINI_MODEL=... を追加。
# モデルが廃止された場合は、API のエラーメッセージが案内する後継へ自動で切り替える（下記）。
DEFAULT_MODEL = "gemini-3.6-flash"
_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class LLMError(Exception):
    pass


def is_mock() -> bool:
    return os.environ.get("PIPELINE_MOCK") == "1" or not os.environ.get("GEMINI_API_KEY")


def _model() -> str:
    # 環境変数が「空文字で存在」しても既定にフォールバックする（CI で vars 未設定のとき対策）
    return (os.environ.get("GEMINI_MODEL") or "").strip() or DEFAULT_MODEL


def model_label() -> str:
    return "mock" if is_mock() else _model()


def generate(prompt: str, *, system: str | None = None, json_mode: bool = False,
             temperature: float = 0.7) -> str:
    if is_mock():
        return _mock(prompt, json_mode=json_mode)

    key = os.environ["GEMINI_API_KEY"]
    model = _model()
    url = _ENDPOINT.format(model=model) + f"?key={key}"

    body: dict = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if json_mode:
        body["generationConfig"]["responseMimeType"] = "application/json"

    data = json.dumps(body).encode("utf-8")
    last = ""
    swapped = False
    for attempt in range(1, 6):
        try:
            req = urllib.request.Request(
                url, data=data, headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            return _extract_text(payload)
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "ignore")
            last = f"HTTP {e.code} (model={model}): {raw[:300]}"
            # モデル廃止 → API が案内する後継モデルに1回だけ自動で切り替える
            if e.code == 404 and not swapped:
                m = re.search(r"use\s+models/([A-Za-z0-9.\-]+)", raw)
                if m and m.group(1) != model:
                    model = m.group(1)
                    url = _ENDPOINT.format(model=model) + f"?key={key}"
                    swapped = True
                    log(f"  LLM: モデルを {model} に自動切替（廃止の案内による）")
                    continue
            if e.code in (408, 429, 500, 502, 503, 504):
                wait = min(2 ** attempt, 30)
                log(f"  LLM retry {attempt} in {wait}s ({e.code})")
                time.sleep(wait)
                continue
            raise LLMError(last)
        except (urllib.error.URLError, TimeoutError) as e:  # noqa: PERF203
            last = str(e)
            time.sleep(min(2 ** attempt, 30))
    raise LLMError(f"LLM failed after retries: {last}")


def generate_json(prompt: str, **kw) -> dict:
    return _loads_loose(generate(prompt, json_mode=True, **kw))


def _extract_text(payload: dict) -> str:
    try:
        parts = payload["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts).strip()
        if not text:
            raise KeyError("empty")
        return text
    except (KeyError, IndexError, TypeError):
        raise LLMError(f"unexpected response: {json.dumps(payload)[:300]}")


def _loads_loose(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        s, e = raw.find("{"), raw.rfind("}")
        if s != -1 and e != -1 and e > s:
            return json.loads(raw[s : e + 1])
        raise


# ---------------------------------------------------------------- mock
_MOCK_BODY = """\
夜、子どもがやっと寝たあとに、この記事を開いてくれてありがとうございます。ここでは誰もあなたを責めません。

## まず、いちばん伝えたいこと

うまくいかない日があっても全然大丈夫です。今日ここまで来られたこと自体が、十分にすごいことです。

> 📊 **MOCK 出典**
> これは GEMINI_API_KEY 未設定時に返るダミーの引用ブロックです。本番では公的機関の要約が入ります。

## 具体的にできること

- できない日は、思いきり水準を下げる
- 便利な道具や制度に頼るのは、心を守るための投資
- 比べる相手は、昨日の自分だけで十分

## まとめ

- これは配線確認用の MOCK 記事
- トーンと構成の枠だけを持っている
- 実データは Gemini 接続後に差し替わる
"""


def _mock(prompt: str, json_mode: bool) -> str:
    if "事実メモ」を" in prompt:  # prompts/research_summarize.md
        return json.dumps(
            {
                "facts": [
                    {
                        "claim": "（MOCK）公的機関は、保護者の負担軽減のために市販品や支援制度の活用を認めている。",
                        "source_label": "MOCK 出典",
                        "source_url": "https://www.cfa.go.jp/",
                    }
                ]
            },
            ensure_ascii=False,
        )
    if "コンセプトリライト" in prompt:  # prompts/concept_rewrite.md
        return json.dumps(
            {
                "title": "（MOCK）これで大丈夫、の話",
                "description": "MOCK。パイプラインの配線確認用ダミー。トーンと構成の枠だけを持っています。実データは Gemini 接続後に生成されます。",
                "body_md": _MOCK_BODY,
            },
            ensure_ascii=False,
        )
    return json.dumps(
        {
            "title": "（MOCK）自動生成のテスト記事",
            "description": "MOCK。GEMINI_API_KEY 未設定のため、配線確認用のダミーを返しています。実運用では競合の構成を参考にした完全オリジナル記事になります。",
            "category": "kokoro",
            "stage": "age0",
            "photo_query": "tired parent holding newborn at home soft light",
            "tags": ["MOCK", "テスト"],
            "emoji": "🧪",
            "body_md": _MOCK_BODY,
            "thumb": {"headline": "これで、大丈夫", "sub": "MOCK 記事", "emoji": "🧪", "accent": "coral"},
        },
        ensure_ascii=False,
    )
