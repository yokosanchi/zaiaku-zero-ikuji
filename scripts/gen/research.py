from __future__ import annotations

import re
import urllib.request

from .llm import generate_json
from .util import log, read_prompt

_UA = "Mozilla/5.0 (compatible; kzi-bot/1.0; +https://zaiaku-zero-ikuji.pages.dev)"


def _fetch(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def _strip(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|nav|footer|header|form|aside).*?</\1>", " ", html)
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    html = re.sub(r"&[a-z#0-9]+;", " ", html)
    return re.sub(r"\s+", " ", html).strip()


def _readable(html: str, limit: int = 4000) -> str:
    try:
        import trafilatura

        txt = trafilatura.extract(html, include_comments=False, include_tables=False) or ""
    except Exception:  # noqa: BLE001 - fall back to the dumb stripper
        txt = _strip(html)
    return re.sub(r"\n{3,}", "\n\n", txt).strip()[:limit]


def _outline_only(html: str) -> list[str]:
    """競合ページからは “見出しの並び” だけを取る（本文は取らない）。"""
    out: list[str] = []
    m = re.search(r"(?is)<title>(.*?)</title>", html)
    if m:
        out.append("title: " + _strip(m.group(1))[:120])
    md = re.search(r'(?is)<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html)
    if md:
        out.append("meta: " + _strip(md.group(1))[:160])
    for tag in ("h1", "h2", "h3"):
        for mm in re.finditer(rf"(?is)<{tag}[^>]*>(.*?)</{tag}>", html):
            t = _strip(mm.group(1))
            if t:
                out.append(f"{tag}: {t[:120]}")
    return out[:40]


def gather(topic: dict) -> dict:
    """公式ソースから事実メモを、競合URLから見出し構成のシグナルを集める。"""
    facts: list[dict] = []
    signals: list[str] = []

    for url in topic.get("official_sources", []) or []:
        try:
            body = _readable(_fetch(url))
        except Exception as e:  # noqa: BLE001
            log(f"  公式ソース取得失敗 {url}: {e}")
            continue
        if not body:
            continue
        prompt = read_prompt("research_summarize").replace("{{URL}}", url).replace("{{TEXT}}", body)
        try:
            res = generate_json(prompt)
            for f in res.get("facts", []):
                f.setdefault("source_url", url)
                f.setdefault("source_label", topic.get("source_label_hint", url))
                facts.append(f)
        except Exception as e:  # noqa: BLE001
            log(f"  要約失敗 {url}: {e}")

    for url in topic.get("ref_urls", []) or []:
        try:
            signals += [f"[競合] {s}" for s in _outline_only(_fetch(url))]
        except Exception as e:  # noqa: BLE001
            log(f"  競合構成の取得失敗 {url}: {e}")

    for sf in topic.get("seed_facts", []) or []:
        facts.append(
            {
                "claim": sf,
                "source_label": topic.get("source_label_hint", "編集部調べ"),
                "source_url": (topic.get("official_sources") or ["https://www.cfa.go.jp/"])[0],
            }
        )

    log(f"  research: facts={len(facts)}  outline_signals={len(signals)}")
    return {"facts": facts, "outline_signals": signals[:60]}
