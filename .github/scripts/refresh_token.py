"""Threads Graph API の長期アクセストークンを自動更新し、GitHub Actions の
リポジトリシークレット `THREADS_ACCESS_TOKEN` をその場で上書きする。

Meta の仕様上、th_refresh_token は「発行から24時間以上経過したトークン」でないと
使えない（生成直後のトークンには使えない）。60日で失効するため、月2回
（1日・15日）の実行で余裕を持って更新し続ける設計。

必須環境変数:
    THREADS_ACCESS_TOKEN  … 現在有効な長期アクセストークン
    THREADS_APP_SECRET    … Meta アプリの App Secret（developers.facebook.com の
                            ユースケース設定「設定」タブに表示される値）
    GH_PAT                … このリポジトリの Actions Secrets を書き換えられる
                            Personal Access Token（fine-grained 推奨、
                            権限は「Secrets: Read and write」だけで足りる）
    GITHUB_REPOSITORY     … "owner/repo"（GitHub Actions が自動で渡す）

依存: requests, pynacl
"""

from __future__ import annotations

import base64
import os
import sys

import requests
from nacl import encoding, public

REFRESH_URL = "https://graph.threads.net/refresh_access_token"
GH_API = "https://api.github.com"
SECRET_NAME = "THREADS_ACCESS_TOKEN"


def _env(name: str) -> str:
    v = os.environ.get(name, "").strip()
    if not v:
        print(f"::error::環境変数 {name} が設定されていません", file=sys.stderr)
        sys.exit(1)
    return v


def refresh_threads_token(current_token: str, app_secret: str) -> str:
    """th_refresh_token でトークンを延長し、新しいトークンを返す。"""
    resp = requests.get(
        REFRESH_URL,
        params={
            "grant_type": "th_refresh_token",
            "access_token": current_token,
            "client_secret": app_secret,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        print(
            f"::error::トークン更新に失敗しました HTTP {resp.status_code}: {resp.text[:500]}",
            file=sys.stderr,
        )
        sys.exit(1)
    data = resp.json()
    new_token = data.get("access_token")
    if not new_token:
        print(f"::error::レスポンスに access_token が含まれていません: {data}", file=sys.stderr)
        sys.exit(1)
    print(f"新しいトークンを取得しました（expires_in={data.get('expires_in')}秒）")
    return new_token


def _gh_headers(pat: str) -> dict:
    return {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def get_public_key(repo: str, pat: str) -> tuple[str, str]:
    url = f"{GH_API}/repos/{repo}/actions/secrets/public-key"
    resp = requests.get(url, headers=_gh_headers(pat), timeout=30)
    if resp.status_code != 200:
        print(f"::error::公開鍵の取得に失敗 HTTP {resp.status_code}: {resp.text[:500]}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    return data["key"], data["key_id"]


def encrypt_secret(public_key_b64: str, secret_value: str) -> str:
    """GitHubのドキュメント通り、libsodiumのsealed boxで暗号化する。"""
    public_key = public.PublicKey(public_key_b64.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def update_secret(repo: str, pat: str, secret_name: str, encrypted_value: str, key_id: str) -> None:
    url = f"{GH_API}/repos/{repo}/actions/secrets/{secret_name}"
    resp = requests.put(
        url,
        headers=_gh_headers(pat),
        json={"encrypted_value": encrypted_value, "key_id": key_id},
        timeout=30,
    )
    if resp.status_code not in (201, 204):
        print(f"::error::Secret更新に失敗 HTTP {resp.status_code}: {resp.text[:500]}", file=sys.stderr)
        sys.exit(1)
    print(f"Secret `{secret_name}` を更新しました（HTTP {resp.status_code}）")


def main() -> None:
    current_token = _env("THREADS_ACCESS_TOKEN")
    app_secret = _env("THREADS_APP_SECRET")
    gh_pat = _env("GH_PAT")
    repo = _env("GITHUB_REPOSITORY")

    new_token = refresh_threads_token(current_token, app_secret)

    key_b64, key_id = get_public_key(repo, gh_pat)
    encrypted = encrypt_secret(key_b64, new_token)
    update_secret(repo, gh_pat, SECRET_NAME, encrypted, key_id)

    print("完了：Threadsアクセストークンを更新し、GitHub Secretsに反映しました。")


if __name__ == "__main__":
    main()
