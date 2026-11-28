#!/usr/bin/env python3
"""【販売者用】販売原稿（product-kit/sales/）とライブデモLP（site/price-kit/index.html）の
URLプレースホルダーを実際の販売URL・相談フォームURLへ抜け漏れなく一括差し替えするスクリプト。

使い方（リポジトリルートから実行）:
  # まず --dry-run で置換内容を確認
  product-kit\\.venv\\Scripts\\python.exe product-kit\\scripts\\apply_sales_urls.py `
    --sales-url "https://note.com/あなたのID/n/xxxxx" `
    --form-url "https://docs.google.com/forms/d/e/xxxxx/viewform" `
    --dry-run

  # 問題なければ --dry-run を外して適用
  product-kit\\.venv\\Scripts\\python.exe product-kit\\scripts\\apply_sales_urls.py `
    --sales-url "https://note.com/あなたのID/n/xxxxx" `
    --booth-url "https://あなたのショップ.booth.pm/items/xxxxx" `
    --form-url "https://docs.google.com/forms/d/e/xxxxx/viewform"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse


KIT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = KIT_ROOT.parent
SALES_DIR = KIT_ROOT / "sales"
LIVE_LP_HTML = REPO_ROOT / "site" / "price-kit" / "index.html"


def _validate_https(url: str, label: str) -> str:
    cleaned = url.strip()
    if not cleaned:
        return ""
    parsed = urlparse(cleaned)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{label} は https:// から始まる正しいURLを指定してください: {cleaned!r}")
    return cleaned


def _replace_in_file(path: Path, replacements: list[tuple[str, str]], *, dry_run: bool) -> int:
    if not path.exists():
        return 0
    original = path.read_text(encoding="utf-8")
    updated = original
    count = 0
    for old, new in replacements:
        if old in updated:
            hits = updated.count(old)
            updated = updated.replace(old, new)
            count += hits
    if count > 0:
        rel = path.relative_to(REPO_ROOT).as_posix()
        mode_tag = "[DRY-RUN]" if dry_run else "[UPDATED]"
        print(f"{mode_tag} {rel} ({count}箇所)")
        if not dry_run:
            path.write_text(updated, encoding="utf-8")
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="販売原稿およびライブデモLPのURLプレースホルダーを一括差し替えします。")
    parser.add_argument("--sales-url", default="", help="メイン販売URL（note / BOOTH / Brain 等）")
    parser.add_argument("--booth-url", default="", help="（任意）BOOTH販売URL。ライブデモLPに併記する場合に指定")
    parser.add_argument("--form-url", default="", help="個別カスタマイズ相談フォームURL（Googleフォーム / ココナラ等）")
    parser.add_argument("--dry-run", action="store_true", help="ファイルを書き換えずに置換対象だけを表示する")
    args = parser.parse_args(argv)

    sales_url = _validate_https(args.sales_url, "--sales-url")
    booth_url = _validate_https(args.booth_url, "--booth-url")
    form_url = _validate_https(args.form_url, "--form-url")

    if not any((sales_url, booth_url, form_url)):
        print("エラー: --sales-url / --booth-url / --form-url のいずれかを1つ以上指定してください。", file=sys.stderr)
        return 2

    total = 0

    if form_url:
        form_replacements = [
            ("`（ここにGoogleフォーム等のURLを記載）`", form_url),
        ]
        total += _replace_in_file(SALES_DIR / "LP_NOTE.md", form_replacements, dry_run=args.dry_run)
        total += _replace_in_file(SALES_DIR / "LP_BRAIN_TIPS.md", form_replacements, dry_run=args.dry_run)

    if sales_url:
        x_replacements = [
            ("[ここに note / BOOTH / Brain の販売URL]", sales_url),
        ]
        total += _replace_in_file(SALES_DIR / "X_LAUNCH_THREAD.md", x_replacements, dry_run=args.dry_run)

        cta_links = f'<a class="btn btn-primary" href="{sales_url}" target="_blank" rel="noopener noreferrer">先行モニター版を購入する →</a>'
        if booth_url:
            cta_links += f' <a class="btn btn-secondary" href="{booth_url}" target="_blank" rel="noopener noreferrer">BOOTHで見る</a>'
        lp_replacements = [
            (
                '<p class="price-note" style="margin:0;">販売プラットフォーム（note / BOOTH / Brain / Tips）の公開ページからご購入いただけます。</p>',
                f'<div class="hero-actions" style="margin-top:14px;">{cta_links}</div>',
            ),
        ]
        total += _replace_in_file(LIVE_LP_HTML, lp_replacements, dry_run=args.dry_run)

    if form_url:
        lp_form_replacements = [
            (
                '<p class="price-note" style="margin:0;">購入者限定の個別相談窓口（商品内案内）からいつでもご依頼いただけます。</p>',
                f'<div class="hero-actions" style="margin-top:14px;"><a class="btn btn-secondary" href="{form_url}" target="_blank" rel="noopener noreferrer">個別カスタマイズを相談する →</a></div>',
            ),
        ]
        total += _replace_in_file(LIVE_LP_HTML, lp_form_replacements, dry_run=args.dry_run)

    if total == 0:
        print("置換対象のプレースホルダーは見つかりませんでした（すでに差し替え済みの可能性があります）。")
    else:
        print(f"\n完了: 合計 {total} 箇所を{'検出' if args.dry_run else '更新'}しました。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
