from __future__ import annotations

import argparse
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .compare import build_comparison
from .config import ConfigError, load_config
from .csv_output import write_outputs
from .http_client import PoliteHttpClient
from .models import PriceItem
from .parsers import collect_source
from .sheets_output import publish_to_sheets


LOGGER = logging.getLogger("price_monitor")
JAPAN_TIME_ZONE = timezone(timedelta(hours=9), name="JST")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="月額サーバー代0円で動く汎用・価格監視＆比較スプレッドシート自動構築ツール"
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="設定ファイルのパス（既定: config.json）",
    )
    parser.add_argument(
        "--output-dir",
        default="data",
        help="CSV・実行サマリーの出力先フォルダ（既定: data）",
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="config.json の書式と安全設定だけを検証して終了する",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="1サイトでも取得エラーが発生したら終了コード1で終了し、Googleシートを上書きしない",
    )
    parser.add_argument(
        "--google-spreadsheet-id",
        default="",
        help="出力先のGoogleスプレッドシートID（未指定時は環境変数 OUTPUT_SPREADSHEET_ID または config.json を使用）",
    )
    parser.add_argument(
        "--google-credentials",
        default="",
        help="Googleサービスアカウント認証JSONのファイルパス",
    )
    return parser


def _print_console_preview(
    *,
    mode: str,
    compared_rows: list,
    alert_rows: list,
    summary: dict,
    output_dir: Path,
) -> None:
    best_label = "最安値" if mode == "lowest" else "最高値"
    print("")
    print(f"=== {summary['project_title']}（モード: {best_label}比較） ===")
    print(
        f"全取得: {summary['record_count']}件 / "
        f"比較対象(2サイト以上): {summary['comparison_count']}件 / "
        f"単独掲載: {summary['single_listing_count']}件 / "
        f"目標達成: {summary['alert_hit_count']}件 / "
        f"エラー: {len(summary['errors'])}件"
    )
    if compared_rows:
        print("\n[価格差が大きい上位5商品]")
        for row in compared_rows[:5]:
            rate_str = f"{row.spread_rate * 100:.1f}%" if row.spread_rate is not None else "-"
            spread_str = f"¥{row.spread_yen:,}" if row.spread_yen is not None else "-"
            hit = " [🎯目標達成]" if row.target_hit else ""
            print(
                f"  - {row.name_normalized} ({row.condition}): "
                f"{best_label} ¥{row.best_price_yen:,} [{row.best_source_label}] / "
                f"差額 {spread_str} ({rate_str}){hit}"
            )
    achieved_alerts = [row for row in alert_rows if row.achieved]
    if achieved_alerts:
        print("\n[🎯 目標価格に到達した商品]")
        for row in achieved_alerts:
            print(
                f"  - {row.item_name}: 現在 ¥{row.current_best_yen:,} "
                f"(目標 ¥{row.target_price_yen:,} / {row.best_source_label})"
            )
    print(f"\n出力先: {output_dir.resolve()}")


def run(args: argparse.Namespace) -> int:
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        LOGGER.error("設定エラー:\n%s", exc)
        return 2

    if args.check_config:
        print(f"✅ 設定ファイルOK: {Path(args.config).resolve()}")
        print(f"   プロジェクト名 : {config.project.title}")
        print(f"   比較モード     : {config.project.comparison_mode}")
        print(f"   有効な取得元   : {len(config.enabled_sources)} サイト")
        print(f"   取得間隔ガード : {config.safety.request_delay_seconds} 秒以上")
        print(f"   robots.txt確認 : {'有効' if config.safety.respect_robots_txt else '無効'}")
        return 0

    fetched_at = datetime.now(JAPAN_TIME_ZONE).isoformat(timespec="seconds")
    client = PoliteHttpClient(config.safety, base_dir=config.config_dir)
    items: list[PriceItem] = []
    errors: dict[str, str] = {}

    for source in config.enabled_sources:
        try:
            LOGGER.info("取得開始: %s (%s)", source.label, source.type)
            source_items = collect_source(source, config, client, fetched_at=fetched_at)
            if not source_items:
                raise RuntimeError(
                    f"取得件数が0件でした。サイトのHTML構造変更やセレクタ設定を確認してください。"
                )
            items.extend(source_items)
            LOGGER.info("取得完了: %s -> %d件", source.label, len(source_items))
        except Exception as exc:
            LOGGER.error("取得エラー (%s): %s", source.label, exc)
            errors[source.id] = str(exc)
            if args.strict:
                break

    compared_rows, single_rows, alert_rows = build_comparison(items, config)
    output_dir = Path(args.output_dir)
    summary = write_outputs(
        output_dir=output_dir,
        config=config,
        items=items,
        compared_rows=compared_rows,
        single_rows=single_rows,
        alert_rows=alert_rows,
        fetched_at=fetched_at,
        errors=errors,
    )

    spreadsheet_id = (
        args.google_spreadsheet_id.strip()
        or os.environ.get("OUTPUT_SPREADSHEET_ID", "").strip()
        or config.project.spreadsheet_id
    )
    credentials_path = args.google_credentials.strip() or os.environ.get("GOOGLE_CREDENTIALS_PATH", "").strip()

    if spreadsheet_id or credentials_path:
        if not (spreadsheet_id and credentials_path):
            LOGGER.error(
                "Googleスプレッドシート出力には --google-spreadsheet-id（または config.json / OUTPUT_SPREADSHEET_ID）と "
                "--google-credentials の両方が必要です。"
            )
            return 2
        if args.strict and errors:
            LOGGER.error("取得エラーがあるため、不完全なデータでGoogleスプレッドシートを上書きしません。")
        else:
            sheet_url = publish_to_sheets(
                spreadsheet_id=spreadsheet_id,
                credentials_file=credentials_path,
                config=config,
                items=items,
                compared_rows=compared_rows,
                single_rows=single_rows,
                alert_rows=alert_rows,
                fetched_at=fetched_at,
                error_count=len(errors),
            )
            LOGGER.info("Googleスプレッドシートを更新しました: %s", sheet_url)

    _print_console_preview(
        mode=config.project.comparison_mode,
        compared_rows=compared_rows,
        alert_rows=alert_rows,
        summary=summary,
        output_dir=output_dir,
    )

    if not items or (args.strict and errors):
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    return run(build_parser().parse_args(argv))
