#!/usr/bin/env python3
"""スマホ手動更新ページ用の「合言葉SHA-256ハッシュ」を安全に生成するツール。

画面やコマンド履歴に合言葉を残さず、Vercelの環境変数 `UPDATE_PASSWORD_HASH` へ
そのまま貼り付けられる64文字のハッシュ値を出力します。
"""

from __future__ import annotations

import getpass
import hashlib
import sys


def main() -> int:
    print("スマホ手動更新用の合言葉を入力してください（入力中は画面に表示されません）。")
    first = getpass.getpass("合言葉（8文字以上推奨）: ")
    if len(first) < 8:
        print("エラー: セキュリティのため、合言葉は8文字以上にしてください。", file=sys.stderr)
        return 1
    second = getpass.getpass("確認のためもう一度入力: ")
    if first != second:
        print("エラー: 2回の入力が一致しませんでした。もう一度お試しください。", file=sys.stderr)
        return 1

    digest = hashlib.sha256(first.encode("utf-8")).hexdigest()
    print("")
    print("=== Vercel の環境変数 UPDATE_PASSWORD_HASH に貼る値 ===")
    print(digest)
    print("=======================================================")
    print("※ この値だけをVercelに貼り付けてください。合言葉の元の文字はコードやGitに書かないでください。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
