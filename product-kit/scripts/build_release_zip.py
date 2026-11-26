#!/usr/bin/env python3
"""配布用ZIPを1コマンドで生成し、秘密情報・不要ファイル混入を自動検査するスクリプト。

使い方:
  python3 product-kit/scripts/build_release_zip.py
  python3 product-kit/scripts/build_release_zip.py --version 1.0.0 --out product-kit/dist/price-monitor-kit-v1.0.0.zip
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import re
import sys
import zipfile
from pathlib import Path


KIT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = KIT_ROOT / "template"
DEFAULT_DIST_DIR = KIT_ROOT / "dist"
DEFAULT_VERSION = "2.0.0"

EXCLUDED_DIR_NAMES = frozenset(
    {
        "__pycache__",
        ".pytest_cache",
        ".venv",
        "venv",
        "node_modules",
        "data",
        "outputs",
        ".git",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
    }
)

EXCLUDED_FILE_PATTERNS = (
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.log",
    ".DS_Store",
    "Thumbs.db",
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*credentials*.json",
    "*service-account*.json",
    "google-key.json",
)

REQUIRED_RELATIVE_PATHS = (
    "README.md",
    "config.json",
    ".gitignore",
    "requirements.txt",
    "requirements-google.txt",
    "requirements-dev.txt",
    ".github/workflows/update-prices.yml",
    "src/price_monitor/__init__.py",
    "src/price_monitor/cli.py",
    "src/price_monitor/config.py",
    "src/price_monitor/http_client.py",
    "src/price_monitor/parsers.py",
    "src/price_monitor/compare.py",
    "src/price_monitor/notifier.py",
    "src/price_monitor/sheets_output.py",
    "custom_collectors/example_custom.py",
    "mobile_updater/index.html",
    "mobile_updater/api/update.js",
    "mobile_updater/cloudflare_worker.js",
    "mobile_updater/wrangler.toml",
    "mobile_updater/vercel.json",
    "tools/config_builder.html",
    "scripts/run_demo.py",
    "scripts/make_passphrase_hash.py",
    "docs/SETUP_GUIDE.md",
    "docs/AI_CUSTOMIZE_PROMPTS.md",
    "docs/TROUBLESHOOTING.md",
    "docs/SAFE_USAGE_GUIDELINES.md",
)

# 配布ZIPのテキスト内に絶対に含まれてはいけない秘密情報・既存運用固有ID
SECRET_AND_LEAK_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("秘密鍵ブロック", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("GoogleサービスアカウントJSON本体", re.compile(r'"type"\s*:\s*"service_account"[\s\S]{0,400}"private_key"\s*:')),
    ("GitHub Classic トークン", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("GitHub Fine-grained トークン", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("Discord 実Webhook URL", re.compile(r"https://(?:discord|discordapp)\.com/api/webhooks/\d{10,}/[A-Za-z0-9_-]{20,}")),
    ("Slack 実Webhook URL", re.compile(r"https://hooks\.slack\.com/services/T[A-Z0-9]{8,}/B[A-Z0-9]{8,}/[A-Za-z0-9]{16,}")),
    ("OpenAI / Anthropic APIキー", re.compile(r"\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}\b")),
    ("Google APIキー", re.compile(r"\bAIzaSy[A-Za-z0-9_-]{20,}\b")),
    ("既存ポケカ運用リポジトリ名/ユーザー名", re.compile(r"keyanbaitian6-cell", re.IGNORECASE)),
    ("既存ポケカ本番スプレッドシートID", re.compile(r"1N3mF4tIjuq8FC3JO5QnT2rPKPn-tu3I8lFLP8ZNysYI")),
    ("既存ポケカ参照シートID", re.compile(r"1uNtzhQBeiPmGR8rjqgwNdesCHbD4Nr6Y4ecZAjBE15g")),
    ("既存ポケカ手動更新URL", re.compile(r"pokeca-price-update\.vercel\.app", re.IGNORECASE)),
    ("既存ポケカ店舗URL (runto)", re.compile(r"runto666\.com", re.IGNORECASE)),
    ("既存ポケカ店舗URL (somurie)", re.compile(r"somurie-kaitori\.com", re.IGNORECASE)),
]

TEXT_EXTENSIONS = frozenset(
    {
        ".py",
        ".js",
        ".json",
        ".md",
        ".txt",
        ".yml",
        ".yaml",
        ".html",
        ".css",
        ".csv",
        ".gitignore",
        ".toml",
        ".sh",
    }
)


def is_excluded(rel_path: Path) -> bool:
    for part in rel_path.parts[:-1]:
        if part in EXCLUDED_DIR_NAMES:
            return True
    name = rel_path.name
    if name in EXCLUDED_DIR_NAMES:
        return True
    return any(fnmatch.fnmatch(name, pattern) for pattern in EXCLUDED_FILE_PATTERNS)


def scan_text_for_leaks(rel_posix: str, text: str) -> list[str]:
    findings: list[str] = []
    for label, pattern in SECRET_AND_LEAK_PATTERNS:
        if pattern.search(text):
            findings.append(f"[{label}] が {rel_posix} で検出されました")
    return findings


def verify_zip_archive(zip_path: Path, *, root_prefix: str) -> list[str]:
    """生成済みZIPの中身を独立して再検証し、問題リストを返す（空なら合格）。"""
    problems: list[str] = []
    if not zip_path.exists():
        return [f"ZIPファイルが存在しません: {zip_path}"]

    with zipfile.ZipFile(zip_path, "r") as zf:
        bad_member = zf.testzip()
        if bad_member is not None:
            problems.append(f"ZIP CRC破損メンバー: {bad_member}")

        names = zf.namelist()
        rel_set: set[str] = set()
        expected_prefix = f"{root_prefix}/"

        for member_name in names:
            if member_name.endswith("/"):
                continue
            if not member_name.startswith(expected_prefix):
                problems.append(f"想定ルートフォルダ外のファイルが含まれています: {member_name}")
                continue
            rel_posix = member_name[len(expected_prefix) :]
            rel_path = Path(rel_posix)
            rel_set.add(rel_posix)

            if is_excluded(rel_path):
                problems.append(f"除外対象ファイルが混入しています: {rel_posix}")

            suffix = rel_path.suffix.lower()
            if suffix in TEXT_EXTENSIONS or rel_path.name in {".gitignore"}:
                try:
                    content = zf.read(member_name).decode("utf-8", errors="replace")
                except Exception as exc:
                    problems.append(f"読み込みエラー ({rel_posix}): {exc}")
                    continue
                problems.extend(scan_text_for_leaks(rel_posix, content))

        for required in REQUIRED_RELATIVE_PATHS:
            if required not in rel_set:
                problems.append(f"必須ファイルが不足しています: {required}")

    return problems


def build_release_zip(
    *,
    template_dir: Path = TEMPLATE_DIR,
    output_zip: Path | None = None,
    version: str = DEFAULT_VERSION,
) -> tuple[Path, int, str]:
    template_root = template_dir.resolve()
    if not template_root.is_dir():
        raise FileNotFoundError(f"テンプレートディレクトリが見つかりません: {template_root}")

    root_prefix = f"price-monitor-kit-v{version}"
    target_zip = (output_zip or (DEFAULT_DIST_DIR / f"{root_prefix}.zip")).resolve()
    target_zip.parent.mkdir(parents=True, exist_ok=True)

    files_to_pack: list[tuple[Path, Path]] = []
    for file_path in sorted(template_root.rglob("*")):
        if not file_path.is_file():
            continue
        rel_path = file_path.relative_to(template_root)
        if is_excluded(rel_path):
            continue
        files_to_pack.append((file_path, rel_path))

    # パッケージ化前に中身を事前スキャン
    pre_scan_issues: list[str] = []
    for file_path, rel_path in files_to_pack:
        if file_path.suffix.lower() in TEXT_EXTENSIONS or file_path.name == ".gitignore":
            text = file_path.read_text(encoding="utf-8", errors="replace")
            pre_scan_issues.extend(scan_text_for_leaks(rel_path.as_posix(), text))
    if pre_scan_issues:
        raise RuntimeError("秘密情報または不要情報の混入を検知したためビルドを中止しました:\n- " + "\n- ".join(pre_scan_issues))

    tmp_zip = target_zip.with_suffix(".zip.tmp")
    try:
        with zipfile.ZipFile(tmp_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for file_path, rel_path in files_to_pack:
                arcname = f"{root_prefix}/{rel_path.as_posix()}"
                zf.write(file_path, arcname=arcname)

        problems = verify_zip_archive(tmp_zip, root_prefix=root_prefix)
        if problems:
            raise RuntimeError("ZIP検証に失敗しました:\n- " + "\n- ".join(problems))

        tmp_zip.replace(target_zip)
    finally:
        if tmp_zip.exists():
            tmp_zip.unlink()

    sha256 = hashlib.sha256(target_zip.read_bytes()).hexdigest()
    return target_zip, len(files_to_pack), sha256


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="配布用デジタル商品ZIPを生成・検証します。")
    parser.add_argument("--version", default=DEFAULT_VERSION, help="バージョン番号（既定: 1.0.0）")
    parser.add_argument("--out", default="", help="出力ZIPパス（省略時: product-kit/dist/price-monitor-kit-v<version>.zip）")
    args = parser.parse_args(argv)

    out_path = Path(args.out) if args.out else None
    zip_path, file_count, sha256 = build_release_zip(version=args.version, output_zip=out_path)
    size_kb = zip_path.stat().st_size / 1024.0
    print("✅ 配布用ZIPの生成＆セキュリティ検証が完了しました！")
    print(f"   出力先   : {zip_path}")
    print(f"   収録数   : {file_count} ファイル")
    print(f"   サイズ   : {size_kb:.1f} KB")
    print(f"   SHA-256  : {sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
