from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

TEMPLATE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TEMPLATE_ROOT / "src"))

from price_monitor.cli import main  # noqa: E402


def test_cli_check_config_succeeds() -> None:
    exit_code = main(["--config", str(TEMPLATE_ROOT / "config.json"), "--check-config"])
    assert exit_code == 0


def test_cli_e2e_demo_run_produces_bom_csvs_and_summary(tmp_path: Path) -> None:
    exit_code = main(
        [
            "--config",
            str(TEMPLATE_ROOT / "config.json"),
            "--output-dir",
            str(tmp_path),
            "--strict",
        ]
    )
    assert exit_code == 0

    for filename in ("raw_prices.csv", "comparison.csv", "single_listings.csv", "alerts.csv", "run_summary.json"):
        assert (tmp_path / filename).exists(), f"{filename} が生成されていません"

    # Excel文字化け防止のUTF-8 BOMが付いていること
    raw_bytes = (tmp_path / "comparison.csv").read_bytes()
    assert raw_bytes.startswith(b"\xef\xbb\xbf")

    summary = json.loads((tmp_path / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["errors"] == {}
    assert summary["record_count"] == 15
    assert summary["comparison_count"] == 5
    assert summary["single_listing_count"] == 1
    assert summary["alert_hit_count"] == 2  # WH-1000XM5 (41,200 <= 42,000) & Switch (34,800 <= 35,000)

    with (tmp_path / "comparison.csv").open("r", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    names = {row["商品名"] for row in rows}
    assert "Sony WH-1000XM5 ワイヤレスヘッドホン" in names
    assert "Nintendo Switch 有機ELモデル ホワイト" in names
    assert "RICOH GR III コンパクトデジタルカメラ" in names
