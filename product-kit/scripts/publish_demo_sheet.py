#!/usr/bin/env python3
"""【販売者用】LP・X告知のスクリーンショット撮影用に、複数日分のデモデータをGoogleスプレッドシートへ一発出力するスクリプト。

外部サイトへは一切アクセスせず、template/sample_pages/ のサンプルデータを使って
過去7日分のリアルな価格推移（SPARKLINE・前回比・7日前比）＋当日の比較・目標アラートを生成します。

使い方（リポジトリルートから実行）:
  product-kit\\.venv\\Scripts\\python.exe product-kit\\scripts\\publish_demo_sheet.py `
    --spreadsheet-id "新規作成したデモ用スプレッドシートID" `
    --credentials "C:\\secure\\google-credentials.json"
"""

from __future__ import annotations

import argparse
import copy
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_ROOT = KIT_ROOT / "template"
sys.path.insert(0, str(TEMPLATE_ROOT / "src"))

from price_monitor.compare import build_comparison  # noqa: E402
from price_monitor.config import load_config  # noqa: E402
from price_monitor.http_client import PoliteHttpClient  # noqa: E402
from price_monitor.models import PriceItem  # noqa: E402
from price_monitor.parsers import collect_source  # noqa: E402
from price_monitor.sheets_output import publish_to_sheets  # noqa: E402


JST = timezone(timedelta(hours=9), name="JST")

DAY_OFFSETS: list[tuple[int, dict[str, int]]] = [
    (7, {"Sony WH-1000XM5": 3600, "Nintendo Switch": 2200, "RICOH GR III": 6000, "AirPods": 1500}),
    (6, {"Sony WH-1000XM5": 3200, "Nintendo Switch": 2000, "RICOH GR III": 5000, "AirPods": 1500}),
    (5, {"Sony WH-1000XM5": 2900, "Nintendo Switch": 1500, "RICOH GR III": 4000, "AirPods": 1000}),
    (4, {"Sony WH-1000XM5": 2400, "Nintendo Switch": 1500, "RICOH GR III": 2500, "AirPods": 1000}),
    (3, {"Sony WH-1000XM5": 1800, "Nintendo Switch": 900, "RICOH GR III": 3000, "AirPods": 500}),
    (2, {"Sony WH-1000XM5": 1200, "Nintendo Switch": 600, "RICOH GR III": 1500, "AirPods": 500}),
    (1, {"Sony WH-1000XM5": 800, "Nintendo Switch": 400, "RICOH GR III": -1000, "AirPods": 0}),
    (0, {}),
]


def _apply_offset(items: list[PriceItem], deltas: dict[str, int], fetched_at: str) -> list[PriceItem]:
    shifted: list[PriceItem] = []
    for item in items:
        cloned = copy.copy(item)
        cloned.fetched_at = fetched_at
        if cloned.price_yen is not None:
            for keyword, delta in deltas.items():
                if keyword.lower() in cloned.name_normalized.lower():
                    cloned.price_yen = max(100, cloned.price_yen + delta)
                    break
        shifted.append(cloned)
    return shifted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="販売用スクショ向けに、過去7日分＋当日のデモデータをGoogleスプレッドシートへ一発出力します。"
    )
    parser.add_argument("--spreadsheet-id", required=True, help="デモ出力先のGoogleスプレッドシートID")
    parser.add_argument("--credentials", required=True, help="Googleサービスアカウント認証JSONのファイルパス")
    parser.add_argument(
        "--days",
        type=int,
        default=8,
        choices=range(2, len(DAY_OFFSETS) + 1),
        help="生成する日数（既定: 8＝7日前〜本日。SPARKLINEと7日前比がすべて埋まります）",
    )
    args = parser.parse_args(argv)

    cfg = load_config(TEMPLATE_ROOT / "config.json")
    client = PoliteHttpClient(cfg.safety, base_dir=cfg.config_dir)

    base_items: list[PriceItem] = []
    now = datetime.now(JST).replace(hour=17, minute=17, second=0, microsecond=0)
    for source in cfg.enabled_sources:
        base_items.extend(collect_source(source, cfg, client, fetched_at=now.isoformat(timespec="seconds")))

    selected_plan = DAY_OFFSETS[-args.days :]
    sheet_url = ""
    for days_ago, deltas in selected_plan:
        run_dt = (now - timedelta(days=days_ago)).isoformat(timespec="seconds")
        day_items = _apply_offset(base_items, deltas, fetched_at=run_dt)
        compared, single, alerts = build_comparison(day_items, cfg)
        sheet_url = publish_to_sheets(
            spreadsheet_id=args.spreadsheet_id.strip(),
            credentials_file=args.credentials.strip(),
            config=cfg,
            items=day_items,
            compared_rows=compared,
            single_rows=single,
            alert_rows=alerts,
            fetched_at=run_dt,
            error_count=0,
        )
        print(f"  ✓ {run_dt[:10]} 分を出力完了")

    print("")
    print("✅ スクショ用デモGoogleスプレッドシートの生成が完了しました！")
    print(f"   URL: {sheet_url}")
    print("   おすすめ撮影タブ: 「比較」「価格推移」「目標アラート」「サマリー」")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
