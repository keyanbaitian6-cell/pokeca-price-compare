from __future__ import annotations

import argparse
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .compare import build_comparison
from .config import AppConfig, ConfigError, load_config
from .csv_output import write_outputs
from .http_client import PoliteHttpClient
from .models import AlertRow, ComparisonRow, PriceItem
from .notifier import send_notifications
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
        "--test-notify",
        action="store_true",
        help="環境変数に設定した Discord / Slack / ntfy.sh へテスト通知を送って終了する",
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
    parser.add_argument(
        "--markdown-summary",
        default="",
        help="スマホ/GitHub Actions画面で見やすいMarkdownサマリーの出力先（未指定時は環境変数 GITHUB_STEP_SUMMARY を自動利用）",
    )
    return parser


def build_markdown_summary(
    *,
    config: AppConfig,
    compared_rows: list[ComparisonRow],
    alert_rows: list[AlertRow],
    summary: dict,
    sheet_url: str = "",
) -> str:
    """GitHub Actions Job Summary（スマホのGitHubアプリでも閲覧可能）用Markdownを生成する。"""
    mode = config.project.comparison_mode
    best_label = "最安値" if mode == "lowest" else "最高値"
    best_store_label = "最安の店" if mode == "lowest" else "最高値の店"

    lines = [
        f"## {summary['project_title']}（{best_label}比較）",
        "",
        f"- **更新日時**: `{summary['fetched_at']}`",
        f"- **全取得**: {summary['record_count']}件 / **比較対象(2サイト以上)**: {summary['comparison_count']}件 / **単独掲載**: {summary['single_listing_count']}件 / **🎯 目標達成**: {summary['alert_hit_count']}件 / **エラー**: {len(summary['errors'])}件",
    ]
    if sheet_url:
        lines.append(f"- **Googleスプレッドシート**: [価格表を開く]({sheet_url})")

    achieved = [row for row in alert_rows if row.achieved]
    if achieved:
        lines.extend(
            [
                "",
                "### 🎯 目標価格に到達した商品",
                f"| 商品名 | 状態 | 目標価格 | 現在{best_label} | {best_store_label} |",
                "| --- | --- | ---: | ---: | --- |",
            ]
        )
        for row in achieved[:20]:
            curr = f"¥{row.current_best_yen:,}" if row.current_best_yen is not None else "-"
            lines.append(
                f"| {row.item_name} | {row.condition} | ¥{row.target_price_yen:,} | {curr} | {row.best_source_label} |"
            )

    if compared_rows:
        lines.extend(
            [
                "",
                "### 価格差が大きい比較商品（上位15件）",
                f"| 商品名 | 状態 | {best_label} | {best_store_label} | 差率 | 差額 | 目標 |",
                "| --- | --- | ---: | --- | ---: | ---: | --- |",
            ]
        )
        for row in compared_rows[:15]:
            rate_str = f"{row.spread_rate * 100:.1f}%" if row.spread_rate is not None else "-"
            spread_str = f"¥{row.spread_yen:,}" if row.spread_yen is not None else "-"
            badge = "🎯 達成" if row.target_hit else ("監視中" if row.target_price_yen is not None else "-")
            lines.append(
                f"| {row.name_normalized} | {row.condition} | ¥{row.best_price_yen:,} | "
                f"{row.best_source_label} | {rate_str} | {spread_str} | {badge} |"
            )

    if summary["errors"]:
        lines.extend(["", "### ⚠️ 取得エラー"])
        for sid, msg in summary["errors"].items():
            lines.append(f"- `{sid}`: {msg}")

    lines.append("")
    return "\n".join(lines)


def _print_console_preview(
    *,
    mode: str,
    compared_rows: list[ComparisonRow],
    alert_rows: list[AlertRow],
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
        print(f"   無料プッシュ通知: {'有効' if config.notifications.enabled else '無効'}")
        return 0

    if args.test_notify:
        res = send_notifications(
            config=config,
            compared_rows=[],
            alert_rows=[],
            summary={"fetched_at": datetime.now(JAPAN_TIME_ZONE).isoformat(timespec="seconds"), "errors": {}},
            force_test=True,
        )
        if res.sent_channels:
            print(f"✅ テスト通知を送信しました: {', '.join(res.sent_channels)}")
            return 0
        if res.errors:
            LOGGER.error("テスト通知の送信に失敗しました: %s", res.errors)
            return 1
        LOGGER.error(
            "テスト通知を送信できませんでした: %s\n"
            "環境変数（DISCORD_WEBHOOK_URL / SLACK_WEBHOOK_URL / NTFY_TOPIC_URL）のいずれかを登録してください。",
            res.skipped_reason,
        )
        return 2

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
                    "取得件数が0件でした。サイトのHTML構造変更やセレクタ設定を確認してください。"
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

    sheet_url = ""
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

    # 無料スマホプッシュ通知（Discord / Slack / ntfy.sh）
    notif_result = send_notifications(
        config=config,
        compared_rows=compared_rows,
        alert_rows=alert_rows,
        summary=summary,
        sheet_url=sheet_url,
    )
    if notif_result.sent_channels:
        LOGGER.info("プッシュ通知を送信しました: %s", ", ".join(notif_result.sent_channels))
    elif notif_result.skipped_reason:
        LOGGER.info("プッシュ通知: %s", notif_result.skipped_reason)

    # GitHub Actions Job Summary（スマホのGitHubアプリから直接結果テーブルを閲覧可能）
    md_path_str = args.markdown_summary.strip() or os.environ.get("GITHUB_STEP_SUMMARY", "").strip()
    if md_path_str:
        md_text = build_markdown_summary(
            config=config,
            compared_rows=compared_rows,
            alert_rows=alert_rows,
            summary=summary,
            sheet_url=sheet_url,
        )
        md_path = Path(md_path_str)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        with md_path.open("a", encoding="utf-8") as fh:
            fh.write(md_text + "\n")

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
