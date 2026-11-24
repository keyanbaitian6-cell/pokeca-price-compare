from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import AppConfig
from .models import AlertRow, ComparisonRow, PriceItem


def _write_csv(path: Path, headers: list[str], rows: list[list[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig（BOM付きUTF-8）で日本語版Excelの文字化けを防ぐ
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        writer.writerows(rows)


def write_outputs(
    *,
    output_dir: Path,
    config: AppConfig,
    items: list[PriceItem],
    compared_rows: list[ComparisonRow],
    single_rows: list[ComparisonRow],
    alert_rows: list[AlertRow],
    fetched_at: str,
    errors: dict[str, str],
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    mode = config.project.comparison_mode
    best_label = "最安値" if mode == "lowest" else "最高値"
    best_store_label = "最安の店" if mode == "lowest" else "最高値の店"
    enabled_sources = config.enabled_sources

    # 1. 全取得レコード (raw_prices.csv)
    raw_headers = [
        "source_id",
        "source_label",
        "name_raw",
        "name_normalized",
        "condition",
        "price_yen",
        "stock_status",
        "url",
        "fetched_at",
        "note",
    ]
    raw_rows = [
        [
            item.source_id,
            item.source_label,
            item.name_raw,
            item.name_normalized,
            item.condition,
            "" if item.price_yen is None else item.price_yen,
            item.stock_status,
            item.url,
            item.fetched_at,
            item.note,
        ]
        for item in items
    ]
    _write_csv(output_dir / "raw_prices.csv", raw_headers, raw_rows)

    # 2. 複数サイト比較 (comparison.csv)
    comp_headers = [
        "商品名",
        "状態",
        best_label,
        best_store_label,
        "差率(%)",
        "差額(円)",
        *[source.label for source in enabled_sources],
        "目標価格",
        "目標判定",
    ]
    comp_csv_rows = [
        [
            row.name_normalized,
            row.condition,
            row.best_price_yen,
            row.best_source_label,
            "" if row.spread_rate is None else f"{row.spread_rate * 100:.1f}",
            "" if row.spread_yen is None else row.spread_yen,
            *[
                "" if row.source_prices.get(source.id) is None else row.source_prices[source.id]
                for source in enabled_sources
            ],
            "" if row.target_price_yen is None else row.target_price_yen,
            "🎯 目標達成" if row.target_hit else ("監視中" if row.target_price_yen is not None else ""),
        ]
        for row in compared_rows
    ]
    _write_csv(output_dir / "comparison.csv", comp_headers, comp_csv_rows)

    # 3. 単独掲載 (single_listings.csv)
    single_headers = ["商品名", "状態", "掲載店", "価格", "URL"]
    single_csv_rows = []
    for row in single_rows:
        first_url = next((url for url in row.source_urls.values() if url), "")
        single_csv_rows.append(
            [row.name_normalized, row.condition, row.best_source_label, row.best_price_yen, first_url]
        )
    _write_csv(output_dir / "single_listings.csv", single_headers, single_csv_rows)

    # 4. 目標アラート (alerts.csv)
    alert_headers = ["判定", "商品名", "状態", "目標価格", f"現在{best_label}", "目標差額", best_store_label, "URL"]
    alert_csv_rows = [
        [
            row.status_label,
            row.item_name,
            row.condition,
            row.target_price_yen,
            "" if row.current_best_yen is None else row.current_best_yen,
            "" if row.diff_yen is None else row.diff_yen,
            row.best_source_label,
            row.url,
        ]
        for row in alert_rows
    ]
    _write_csv(output_dir / "alerts.csv", alert_headers, alert_csv_rows)

    # 5. 実行サマリー (run_summary.json)
    source_counts: dict[str, int] = {}
    for item in items:
        source_counts[item.source_id] = source_counts.get(item.source_id, 0) + 1

    summary: dict[str, Any] = {
        "fetched_at": fetched_at,
        "project_title": config.project.title,
        "comparison_mode": mode,
        "record_count": len(items),
        "comparison_count": len(compared_rows),
        "single_listing_count": len(single_rows),
        "alert_target_count": len(alert_rows),
        "alert_hit_count": sum(1 for row in alert_rows if row.achieved),
        "source_record_counts": source_counts,
        "errors": errors,
    }
    (output_dir / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary
