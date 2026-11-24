from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT_ROOT / "scripts"))

from build_release_zip import build_release_zip, verify_zip_archive  # noqa: E402


def test_build_release_zip_passes_all_checks_and_runs_cleanly_after_extract(tmp_path: Path) -> None:
    out_zip = tmp_path / "price-monitor-kit-v1.0.0.zip"
    zip_path, file_count, sha256 = build_release_zip(version="1.0.0", output_zip=out_zip)

    assert zip_path.exists()
    assert file_count >= 25
    assert len(sha256) == 64
    assert verify_zip_archive(zip_path, root_prefix="price-monitor-kit-v1.0.0") == []

    # 実際に解凍した状態でもデモが1コマンドで正常動作することを検証
    extract_dir = tmp_path / "extracted"
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    unpacked_root = extract_dir / "price-monitor-kit-v1.0.0"
    assert (unpacked_root / "config.json").exists()
    assert (unpacked_root / "docs" / "AI_CUSTOMIZE_PROMPTS.md").exists()

    proc = subprocess.run(
        [sys.executable, str(unpacked_root / "scripts" / "run_demo.py")],
        cwd=unpacked_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"解凍後デモ実行失敗:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    assert (unpacked_root / "data" / "comparison.csv").exists()
    assert (unpacked_root / "data" / "alerts.csv").exists()


def test_build_release_zip_excludes_junk_and_blocks_secret_leaks(tmp_path: Path) -> None:
    # テンプレートを一時コピーし、不要ファイルと秘密ファイルを混ぜて安全防御を検証
    fake_template = tmp_path / "template_copy"
    shutil.copytree(
        KIT_ROOT / "template",
        fake_template,
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "data", ".venv"),
    )

    # 除外されるべき不要ファイル・認証ファイルを作成
    (fake_template / ".env").write_text("SECRET=123\n", encoding="utf-8")
    (fake_template / "my-service-account.json").write_text('{"type": "service_account"}', encoding="utf-8")
    (fake_template / "data").mkdir(exist_ok=True)
    (fake_template / "data" / "raw_prices.csv").write_text("dummy", encoding="utf-8")
    (fake_template / "__pycache__").mkdir(exist_ok=True)
    (fake_template / "__pycache__" / "x.pyc").write_bytes(b"pyc")

    out_zip = tmp_path / "clean.zip"
    zip_path, _, _ = build_release_zip(template_dir=fake_template, output_zip=out_zip, version="1.0.0")

    with zipfile.ZipFile(zip_path, "r") as zf:
        members = zf.namelist()
    assert not any(m.endswith(".env") for m in members)
    assert not any("service-account" in m for m in members)
    assert not any("/data/" in m for m in members)
    assert not any("__pycache__" in m for m in members)

    # コード内に秘密鍵が紛れ込んだ場合は必ずビルド失敗すること
    (fake_template / "README.md").write_text(
        "leaked -----BEGIN PRIVATE KEY-----\nMIIE...\n", encoding="utf-8"
    )
    with pytest.raises(RuntimeError, match="秘密鍵ブロック"):
        build_release_zip(template_dir=fake_template, output_zip=tmp_path / "fail.zip", version="1.0.0")
