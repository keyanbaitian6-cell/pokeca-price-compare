#!/usr/bin/env python3
"""【販売者用】公開リポジトリから有料商品本体（product-kit/）を別 Private リポジトリへ
安全分離するための移行フォルダ生成スクリプト。

既存リポジトリのファイルは一切変更・削除しません（コピー＆検証のみ）。

使い方:
  product-kit\\.venv\\Scripts\\python.exe product-kit\\scripts\\prepare_private_repo.py `
    --dest "C:\\Users\\keyan\\works\\price-monitor-kit-private" `
    --dry-run
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parent.parent

EXCLUDED_DIRS = frozenset({".venv", "venv", "dist", "__pycache__", ".pytest_cache", "node_modules", "data", ".git"})
EXCLUDED_SUFFIXES = frozenset({".pyc", ".pyo", ".pyd", ".log"})
EXCLUDED_NAMES = frozenset({".DS_Store", "Thumbs.db", ".env"})

PRIVATE_ROOT_GITIGNORE = """# Private repo ignores
.venv/
venv/
__pycache__/
.pytest_cache/
product-kit/.venv/
product-kit/dist/
product-kit/template/data/
*.pyc
*.log
.env
.env.*
*credentials*.json
*service-account*.json
google-key.json
.DS_Store
Thumbs.db
"""


def _should_skip(rel_path: Path) -> bool:
    if any(part in EXCLUDED_DIRS for part in rel_path.parts):
        return True
    if rel_path.name in EXCLUDED_NAMES or rel_path.suffix.lower() in EXCLUDED_SUFFIXES:
        return True
    if "credentials" in rel_path.name.lower() or "service-account" in rel_path.name.lower():
        return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Private リポジトリ移行用の独立フォルダを安全に生成します。")
    parser.add_argument("--dest", required=True, help="移行先の新しい空フォルダパス")
    parser.add_argument("--dry-run", action="store_true", help="実際には書き込まず対象ファイル数だけ表示する")
    args = parser.parse_args(argv)

    dest_root = Path(args.dest).resolve()
    if dest_root == KIT_ROOT or KIT_ROOT in dest_root.parents or dest_root in KIT_ROOT.parents:
        print("エラー: 移行先パスは現在のリポジトリ外を指定してください。", file=sys.stderr)
        return 2

    files: list[tuple[Path, Path]] = []
    for path in sorted(KIT_ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(KIT_ROOT)
        if _should_skip(rel):
            continue
        files.append((path, rel))

    if args.dry_run:
        print(f"[DRY-RUN] 移行先: {dest_root}")
        print(f"[DRY-RUN] コピー予定ファイル数: {len(files)} ファイル (+ ルート .gitignore / README.md)")
        for _, rel in files[:15]:
            print(f"  - product-kit/{rel.as_posix()}")
        if len(files) > 15:
            print(f"  ... 他 {len(files) - 15} ファイル")
        return 0

    if dest_root.exists() and any(dest_root.iterdir()):
        print(f"エラー: 移行先フォルダが既に存在し空ではありません: {dest_root}", file=sys.stderr)
        return 2

    dest_kit = dest_root / "product-kit"
    dest_kit.mkdir(parents=True, exist_ok=True)
    for src, rel in files:
        dst = dest_kit / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    (dest_root / ".gitignore").write_text(PRIVATE_ROOT_GITIGNORE, encoding="utf-8")
    (dest_root / "README.md").write_text(
        "# Price Monitor Kit（Private 管理リポジトリ）\n\n"
        "有料デジタル商品『月額サーバー代0円・価格監視＆比較スプレッドシート自動構築キット』の非公開管理リポジトリです。\n\n"
        "- 管理・テスト・出荷手順: [`product-kit/README.md`](product-kit/README.md)\n"
        "- 収益防衛・分離ガイド: [`product-kit/docs/PRIVATE_REPO_MIGRATION.md`](product-kit/docs/PRIVATE_REPO_MIGRATION.md)\n",
        encoding="utf-8",
    )

    print("✅ Private リポジトリ用フォルダの生成が完了しました！")
    print(f"   出力先   : {dest_root}")
    print(f"   収録数   : {len(files)} ファイル (+ ルート .gitignore / README.md)")
    print("   次の手順 : product-kit/docs/PRIVATE_REPO_MIGRATION.md の STEP 2 に沿って Private リポジトリへ push してください。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
