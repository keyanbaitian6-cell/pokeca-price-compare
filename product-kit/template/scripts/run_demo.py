#!/usr/bin/env python3
"""外部サイトへ一切アクセスせず、付属サンプルHTML/CSVで動作確認できる1コマンドデモ。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from price_monitor.cli import main  # noqa: E402


if __name__ == "__main__":
    config_path = str(ROOT / "config.json")
    output_dir = str(ROOT / "data")
    raise SystemExit(main(["--config", config_path, "--output-dir", output_dir]))
