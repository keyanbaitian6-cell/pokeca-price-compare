from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from .collectors.collect_sheet import fetch_collect_records
from .collectors.runto import fetch_runto_records
from .collectors.somurie import fetch_somurie_records
from .compare import build_box_comparison, records_to_frame
from .google_output import (
    TREND_HEADERS,
    _merge_trend_history,
    _shrink_trend_frame,
    publish_frames,
)
from .http import PoliteRequester, build_session
from .market_analysis import analyze_market
from .models import PriceRecord
from .prompt_builder import (
    TOOL_SITE_BASE_URL,
    build_prompt_bundle,
    write_prompt_outputs,
)


LOGGER = logging.getLogger("card_price_compare")
JAPAN_TIME_ZONE = timezone(timedelta(hours=9), name="JST")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="未開封ポケカBOXの買取価格を比較します。")
    parser.add_argument(
        "--sources",
        default="runto,somurie",
        help="runto,somurie,collect のカンマ区切り（既定: runto,somurie。collect は一時中断）",
    )
    parser.add_argument("--output-dir", default="data", help="CSV保存先")
    parser.add_argument("--request-delay", type=float, default=1.0, help="同一処理内のHTTPアクセス間隔（秒）")
    parser.add_argument("--runto-max-pages", type=int, default=0, help="0は全ページ")
    parser.add_argument("--no-runto-variants", action="store_true", help="runtoの商品詳細を巡回しない")
    parser.add_argument("--somurie-headed", action="store_true", help="買取ソムリエ取得時にブラウザーを表示")
    parser.add_argument("--strict", action="store_true", help="1サイトの失敗でも終了コード1にする")
    parser.add_argument("--google-spreadsheet-id", help="比較結果を書き込む別のGoogleスプレッドシートID")
    parser.add_argument("--google-credentials", help="GoogleサービスアカウントJSONのパス")
    parser.add_argument(
        "--trend-history-csv",
        help="ローカル日次推移CSVのパス（省略時は <output-dir>/shrink_trend_history.csv）",
    )
    parser.add_argument(
        "--skip-prompts",
        action="store_true",
        help="市況分析・発信プロンプトの生成および「発信プロンプト」タブ更新をスキップする",
    )
    parser.add_argument(
        "--from-local-data",
        action="store_true",
        help="外部サイトへアクセスせず、既存の比較CSV・推移CSVから発信プロンプトのみ再生成する",
    )
    parser.add_argument(
        "--tool-url",
        default=TOOL_SITE_BASE_URL,
        help="発信プロンプトへ組み込む無料計算ツールURL（既定: トレカ損益ラボ）",
    )
    return parser


def _write_csv(frame: object, path: Path) -> None:
    # utf-8-sig lets Japanese Windows Excel open the CSV without mojibake.
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def _load_csv_safely(path: Path, *, expected_columns: list[str] | None = None) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=expected_columns or [])
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except Exception:
        LOGGER.warning("CSVの読み込みに失敗したため空データとして扱います: %s", path)
        return pd.DataFrame(columns=expected_columns or [])


def _update_local_trend_history(
    trend_path: Path,
    comparison: pd.DataFrame,
    *,
    raw: pd.DataFrame,
    fetched_at: str,
) -> pd.DataFrame:
    """Persist local daily shrink-wrapped price history alongside CSV outputs."""
    existing = _load_csv_safely(trend_path, expected_columns=TREND_HEADERS)
    if not set(TREND_HEADERS).issubset(existing.columns):
        existing = pd.DataFrame(columns=TREND_HEADERS)
    current = _shrink_trend_frame(comparison, fetched_at=fetched_at, raw=raw)
    merged = _merge_trend_history(existing, current)
    if not merged.empty:
        trend_path.parent.mkdir(parents=True, exist_ok=True)
        _write_csv(merged, trend_path)
    return merged


def run(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    # GitHub-hosted runners use UTC. Record the business timestamp in Japan time
    # so local and cloud executions produce the same update history.
    fetched_at = datetime.now(JAPAN_TIME_ZONE).isoformat(timespec="seconds")
    trend_path = (
        Path(args.trend_history_csv)
        if getattr(args, "trend_history_csv", None)
        else output_dir / "shrink_trend_history.csv"
    )
    tool_url = getattr(args, "tool_url", TOOL_SITE_BASE_URL) or TOOL_SITE_BASE_URL
    skip_prompts = bool(getattr(args, "skip_prompts", False))

    if getattr(args, "from_local_data", False):
        comparison = _load_csv_safely(output_dir / "box_comparison.csv")
        trend_history = _load_csv_safely(trend_path, expected_columns=TREND_HEADERS)
        insights = analyze_market(comparison, trend_history, fetched_at=fetched_at)
        bundle = build_prompt_bundle(insights, tool_base_url=tool_url)
        prompt_paths = write_prompt_outputs(insights, bundle, output_dir)
        LOGGER.info(
            "ローカルデータから発信プロンプトを再生成しました: %s",
            prompt_paths["ai_prompts_md"],
        )
        return 0

    requested_sources = {part.strip().lower() for part in args.sources.split(",") if part.strip()}
    unknown = requested_sources - {"collect", "runto", "somurie"}
    if unknown:
        raise ValueError(f"未対応の取得元です: {', '.join(sorted(unknown))}")

    records: list[PriceRecord] = []
    errors: dict[str, str] = {}
    requester = PoliteRequester(build_session(), delay_seconds=max(args.request_delay, 0.5))

    for source in ("collect", "runto", "somurie"):
        if source not in requested_sources:
            continue
        try:
            LOGGER.info("%s の取得を開始します", source)
            if source == "collect":
                source_records = fetch_collect_records(requester, fetched_at=fetched_at)
            elif source == "runto":
                source_records = fetch_runto_records(
                    requester,
                    max_pages=args.runto_max_pages or None,
                    resolve_variants=not args.no_runto_variants,
                    fetched_at=fetched_at,
                )
            else:
                source_records = fetch_somurie_records(
                    headless=not args.somurie_headed,
                    fetched_at=fetched_at,
                )
            records.extend(source_records)
            LOGGER.info("%s: %d件取得", source, len(source_records))
        except Exception as exc:  # Keep independent sites usable when one layout changes.
            LOGGER.exception("%s の取得に失敗しました", source)
            errors[source] = str(exc)
            if args.strict:
                break

    raw = records_to_frame(records)
    comparison = build_box_comparison(raw)
    _write_csv(raw, output_dir / "raw_prices.csv")
    _write_csv(comparison, output_dir / "box_comparison.csv")

    local_trend_history = _update_local_trend_history(
        trend_path, comparison, raw=raw, fetched_at=fetched_at
    )
    prompt_files: dict[str, str] = {}
    sentiment_summary: dict[str, object] = {}
    if not skip_prompts:
        insights = analyze_market(comparison, local_trend_history, fetched_at=fetched_at)
        bundle = build_prompt_bundle(insights, tool_base_url=tool_url)
        written_paths = write_prompt_outputs(insights, bundle, output_dir)
        prompt_files = {key: str(path.name) for key, path in written_paths.items()}
        sentiment_summary = {
            "mood_label": insights.sentiment.mood_label,
            "prev_up_count": insights.sentiment.prev_up_count,
            "prev_down_count": insights.sentiment.prev_down_count,
            "week_up_count": insights.sentiment.week_up_count,
            "week_down_count": insights.sentiment.week_down_count,
            "high_spread_box_count": insights.high_spread_box_count,
        }

    summary = {
        "fetched_at": fetched_at,
        "requested_sources": sorted(requested_sources),
        "record_count": len(raw),
        "comparison_count": len(comparison),
        "source_record_counts": (
            {str(key): int(value) for key, value in raw.groupby("source").size().items()} if not raw.empty else {}
        ),
        "matched_site_counts": (
            {
                str(int(key)): int(value)
                for key, value in comparison.groupby("matched_site_count").size().items()
            }
            if not comparison.empty
            else {}
        ),
        "condition_inferred_count": (
            int(comparison["condition_inferred"].sum()) if not comparison.empty else 0
        ),
        "high_spread_over_20pct": (
            comparison[
                (comparison["matched_site_count"] >= 2)
                & comparison["spread_yen"].notna()
                & (comparison["best_price_yen"] > 0)
                & (comparison["spread_yen"] / comparison["best_price_yen"] > 0.20)
            ][
                ["product_name_normalized", "condition", "best_price_yen", "spread_yen"]
            ].to_dict(orient="records")
            if not comparison.empty
            else []
        ),
        "market_sentiment": sentiment_summary,
        "prompt_files": prompt_files,
        "errors": errors,
    }
    (output_dir / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if args.google_spreadsheet_id or args.google_credentials:
        if not (args.google_spreadsheet_id and args.google_credentials):
            raise ValueError("Google出力には --google-spreadsheet-id と --google-credentials の両方が必要です。")
        if args.strict and errors:
            LOGGER.error("取得エラーがあるため、不完全なデータでGoogleシートを上書きしません。")
        else:
            url = publish_frames(
                spreadsheet_id=args.google_spreadsheet_id,
                credentials_file=args.google_credentials,
                comparison=comparison,
                raw=raw,
                fetched_at=fetched_at,
                error_count=len(errors),
                prompt_output_dir=None if skip_prompts else output_dir,
                skip_prompts=skip_prompts,
                tool_base_url=tool_url,
            )
            LOGGER.info("Googleスプレッドシートを更新しました: %s", url)

    LOGGER.info("完了: raw=%d件 comparison=%d件 errors=%d件", len(raw), len(comparison), len(errors))
    if not records or (args.strict and errors):
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    return run(build_parser().parse_args(argv))
