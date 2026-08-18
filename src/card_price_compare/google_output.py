from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta, timezone

import pandas as pd

from .collectors.collect_sheet import SPREADSHEET_ID as COLLECT_SOURCE_SPREADSHEET_ID


COMPARISON_HEADERS = {
    "product_name_normalized": "商品名（名寄せ後）",
    "condition": "状態",
    "condition_inferred": "状態の注意",
    "collect_price_yen": "コレクト",
    "runto_price_yen": "runto",
    "somurie_price_yen": "買取ソムリエ",
    "best_site": "最高値サイト",
    "best_price_yen": "最高買取価格",
    "spread_yen": "価格差",
    "matched_site_count": "比較サイト数",
    "collect_name": "コレクト商品名",
    "runto_name": "runto商品名",
    "somurie_name": "買取ソムリエ商品名",
}
RAW_HEADERS = {
    "source": "取得元",
    "product_name_raw": "商品名（原文）",
    "product_name_normalized": "商品名（名寄せ後）",
    "match_key": "照合キー",
    "variant": "バリエーション",
    "condition": "状態",
    "product_kind": "商品区分",
    "price_yen": "買取価格",
    "price_min_yen": "最低価格",
    "price_max_yen": "最高価格",
    "stock_status": "受付状態",
    "product_url": "商品URL",
    "source_updated_label": "元データ更新日",
    "fetched_at": "取得日時",
    "notes": "備考",
}

CONDITION_LABELS = {
    "shrink_wrapped": "シュリンク有",
    "no_shrink": "シュリンク無",
    "no_perforation": "ぺりぺり無",
    "unspecified": "状態不明",
    "sealed_unspecified": "未開封（状態不明）",
}

HISTORY_HEADERS = ["実行日時", "全取得レコード", "比較行", "3サイト一致", "2サイト一致", "取得エラー"]
JAPAN_TIME_ZONE = timezone(timedelta(hours=9), name="JST")


def _sheet_values(frame: pd.DataFrame) -> list[list[object]]:
    cleaned = frame.astype(object).where(pd.notna(frame), "")
    return [list(frame.columns)] + cleaned.values.tolist()


def _display_condition(value: object) -> object:
    """Keep stable English codes internally and localize only user-facing sheets."""
    return CONDITION_LABELS.get(str(value), value)


def _comparison_sheet_frame(frame: pd.DataFrame) -> pd.DataFrame:
    prepared = frame.rename(columns=COMPARISON_HEADERS).copy()
    if "状態" in prepared:
        prepared["状態"] = prepared["状態"].map(_display_condition)
    if "状態の注意" in prepared:
        prepared["状態の注意"] = prepared["状態の注意"].map(
            lambda value: "一部店舗で状態不明" if bool(value) else ""
        )
    return prepared


def _raw_sheet_frame(frame: pd.DataFrame) -> pd.DataFrame:
    prepared = frame.rename(columns=RAW_HEADERS).copy()
    if "状態" in prepared:
        prepared["状態"] = prepared["状態"].map(_display_condition)
    return prepared


def _history_row(
    comparison: pd.DataFrame,
    raw: pd.DataFrame,
    *,
    fetched_at: str,
    error_count: int,
) -> list[object]:
    timestamp = (
        datetime.fromisoformat(fetched_at)
        .astimezone(JAPAN_TIME_ZONE)
        .strftime("%Y-%m-%d %H:%M")
    )
    if comparison.empty or "matched_site_count" not in comparison:
        three_site_count = 0
        two_site_count = 0
    else:
        counts = comparison["matched_site_count"].value_counts()
        three_site_count = int(counts.get(3, 0))
        two_site_count = int(counts.get(2, 0))
    return [
        timestamp,
        int(len(raw)),
        int(len(comparison)),
        three_site_count,
        two_site_count,
        int(error_count),
    ]


def _ensure_summary_sheet(spreadsheet: object) -> None:
    try:
        summary = spreadsheet.worksheet("サマリー")
    except Exception as exc:
        # Avoid importing gspread exception classes in this helper.
        if exc.__class__.__name__ != "WorksheetNotFound":
            raise
        summary = spreadsheet.add_worksheet(title="サマリー", rows=30, cols=9)
        summary.update(
            values=[
                ["ポケカ買取価格表（手動更新）"],
                [],
                ["最終更新", "=IFERROR(MAX(更新履歴!A2:A),\"\")"],
                ["全取得レコード", "=IFERROR(LOOKUP(2,1/(更新履歴!A:A<>\"\"),更新履歴!B:B),0)"],
                ["BOX比較件数", "=IFERROR(LOOKUP(2,1/(更新履歴!A:A<>\"\"),更新履歴!C:C),0)"],
                ["3サイト一致", "=IFERROR(LOOKUP(2,1/(更新履歴!A:A<>\"\"),更新履歴!D:D),0)"],
                ["2サイト一致", "=IFERROR(LOOKUP(2,1/(更新履歴!A:A<>\"\"),更新履歴!E:E),0)"],
                ["取得エラー", "=IFERROR(LOOKUP(2,1/(更新履歴!A:A<>\"\"),更新履歴!F:F),0)"],
            ],
            range_name="A1",
            value_input_option="USER_ENTERED",
        )
    summary.update_acell("A1", "ポケカ買取価格表（手動更新）")


def publish_frames(
    *,
    spreadsheet_id: str,
    credentials_file: str | Path,
    comparison: pd.DataFrame,
    raw: pd.DataFrame,
    fetched_at: str | None = None,
    error_count: int = 0,
) -> str:
    """Refresh output tabs and append history; never write to the Collect source sheet."""
    if spreadsheet_id == COLLECT_SOURCE_SPREADSHEET_ID:
        raise ValueError("コレクトの参照元スプレッドシートを出力先には指定できません。")
    try:
        import gspread
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("Google出力には requirements-google.txt の導入が必要です。") from exc

    client = gspread.service_account(filename=str(credentials_file))
    spreadsheet = client.open_by_key(spreadsheet_id)
    spreadsheet.update_title("ポケカ買取価格表（手動更新）")
    sheet_frames = (
        ("比較", _comparison_sheet_frame(comparison)),
        ("全取得", _raw_sheet_frame(raw)),
    )
    for title, frame in sheet_frames:
        try:
            worksheet = spreadsheet.worksheet(title)
            worksheet.clear()
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(
                title=title,
                rows=max(len(frame) + 10, 100),
                cols=max(len(frame.columns) + 2, 20),
            )
        values = _sheet_values(frame)
        worksheet.update(values=values, range_name="A1", value_input_option="RAW")
        worksheet.freeze(rows=1)

    try:
        history = spreadsheet.worksheet("更新履歴")
    except gspread.WorksheetNotFound:
        history = spreadsheet.add_worksheet(title="更新履歴", rows=1000, cols=len(HISTORY_HEADERS))
    if not history.get("A1:F1"):
        history.update(values=[HISTORY_HEADERS], range_name="A1", value_input_option="RAW")
        history.freeze(rows=1)

    effective_fetched_at = fetched_at
    if not effective_fetched_at and not raw.empty and "fetched_at" in raw:
        effective_fetched_at = str(raw["fetched_at"].dropna().iloc[0])
    if not effective_fetched_at:
        effective_fetched_at = datetime.now(JAPAN_TIME_ZONE).isoformat(timespec="seconds")
    history.append_row(
        _history_row(
            comparison,
            raw,
            fetched_at=effective_fetched_at,
            error_count=error_count,
        ),
        value_input_option="USER_ENTERED",
    )
    _ensure_summary_sheet(spreadsheet)
    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
