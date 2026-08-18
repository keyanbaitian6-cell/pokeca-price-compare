from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta, timezone

import pandas as pd

from .collectors.collect_sheet import SPREADSHEET_ID as COLLECT_SOURCE_SPREADSHEET_ID


SOURCE_LABELS = {
    "collect": "コレクト",
    "runto": "runto",
    "somurie": "買取ソムリエ",
}
PRICE_COLUMN_LABELS = ["コレクト", "runto", "買取ソムリエ"]
PRICE_SOURCE_COLUMNS = ["collect_price_yen", "runto_price_yen", "somurie_price_yen"]

# The comparison tab only answers "which store pays more"; the original store
# names stay on the raw tab so this table can stay narrow enough to read.
COMPARISON_COLUMNS = [
    "商品名",
    "状態",
    "最高値",
    "最高値の店",
    "差率",
    "差額",
    "コレクト",
    "runto",
    "買取ソムリエ",
    "注意",
]
COMPARISON_SOURCE_COLUMNS = [
    "product_name_normalized",
    "condition",
    "condition_inferred",
    "collect_price_yen",
    "runto_price_yen",
    "somurie_price_yen",
    "best_site",
    "best_price_yen",
    "spread_yen",
    "matched_site_count",
]
SINGLE_LISTING_COLUMNS = ["商品名", "状態", "掲載店", "買取価格"]

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
# Shown in the narrow 注意 column. The full meaning is "some stores did not
# state the condition", recorded in docs/DECISIONS.md.
CONDITION_INFERRED_LABEL = "状態推定"
ALL_SITES_TIED_LABEL = "3店同額"

COMPARISON_SHEET_TITLE = "比較"
SINGLE_LISTING_SHEET_TITLE = "単独掲載"
RAW_SHEET_TITLE = "全取得"
HISTORY_SHEET_TITLE = "更新履歴"
SUMMARY_SHEET_TITLE = "サマリー"

HISTORY_HEADERS = [
    "実行日時",
    "全取得レコード",
    "比較行（2サイト以上）",
    "3サイト一致",
    "2サイト一致",
    "取得エラー",
    "1サイトのみ",
]
JAPAN_TIME_ZONE = timezone(timedelta(hours=9), name="JST")
MANUAL_UPDATE_URL = "https://pokeca-price-update.vercel.app"
MANUAL_UPDATE_FORMULA = f'=HYPERLINK("{MANUAL_UPDATE_URL}","🔄 価格表を手動更新")'

# Row 9 holds the merged manual update link, so the counters stop at row 8 and
# the error counter continues below the link.
SUMMARY_COUNTER_RANGE = "A3"
SUMMARY_ERROR_RANGE = "A11"
SUMMARY_COUNTER_ROWS = [
    ["最終更新", '=IFERROR(MAX(更新履歴!A2:A),"")'],
    ["全取得レコード", '=IFERROR(LOOKUP(2,1/(更新履歴!A:A<>""),更新履歴!B:B),0)'],
    ["BOX比較件数（2サイト以上）", '=IFERROR(LOOKUP(2,1/(更新履歴!A:A<>""),更新履歴!C:C),0)'],
    ["3サイト一致", '=IFERROR(LOOKUP(2,1/(更新履歴!A:A<>""),更新履歴!D:D),0)'],
    ["2サイト一致", '=IFERROR(LOOKUP(2,1/(更新履歴!A:A<>""),更新履歴!E:E),0)'],
    ["1サイトのみ（単独掲載）", '=IFERROR(LOOKUP(2,1/(更新履歴!A:A<>""),更新履歴!G:G),0)'],
]
SUMMARY_ERROR_ROW = [
    ["取得エラー", '=IFERROR(LOOKUP(2,1/(更新履歴!A:A<>""),更新履歴!F:F),0)']
]

HIGH_SPREAD_RATE = 0.05
YEN_PATTERN = "¥#,##0"
RATE_PATTERN = "0.0%"
HEADER_BACKGROUND_HEX = "1F3864"
BEST_PRICE_BACKGROUND_HEX = "C6EFCE"
WARNING_BACKGROUND_HEX = "FFF2CC"
HIGH_SPREAD_TEXT_HEX = "C00000"

COMPARISON_COLUMN_WIDTHS = [300, 100, 90, 130, 70, 90, 90, 90, 100, 80]
SINGLE_LISTING_COLUMN_WIDTHS = [300, 100, 110, 110]
RAW_COLUMN_WIDTHS = [80, 300, 220, 220, 110, 100, 100, 100, 100, 100, 90, 220, 120, 150, 150]


def _sheet_values(frame: pd.DataFrame) -> list[list[object]]:
    cleaned = frame.astype(object).where(pd.notna(frame), "")
    return [list(frame.columns)] + cleaned.values.tolist()


def _display_condition(value: object) -> object:
    """Keep stable English codes internally and localize only user-facing sheets."""
    return CONDITION_LABELS.get(str(value), value)


def _optional_int(value: object) -> object:
    if value is None or value is pd.NA:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        return ""
    try:
        return int(value)
    except (TypeError, ValueError):
        return ""


def _store_label(value: object) -> str:
    """Turn the internal best_site code list into a readable store name."""
    sources = [part.strip() for part in str(value or "").split(",") if part.strip()]
    if not sources:
        return ""
    if len(sources) >= len(SOURCE_LABELS):
        return ALL_SITES_TIED_LABEL
    return "・".join(SOURCE_LABELS.get(source, source) for source in sources)


def _has_comparison_columns(frame: pd.DataFrame) -> bool:
    return not frame.empty and set(COMPARISON_SOURCE_COLUMNS).issubset(frame.columns)


def split_comparison(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split the comparison result into "two or more stores" and "single store"."""
    if not _has_comparison_columns(frame):
        empty = frame.iloc[0:0] if isinstance(frame, pd.DataFrame) else pd.DataFrame()
        return empty.copy(), empty.copy()
    counts = pd.to_numeric(frame["matched_site_count"], errors="coerce").fillna(0)
    return frame[counts >= 2].copy(), frame[counts == 1].copy()


def _comparison_sheet_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Build the 比較 tab: only rows that at least two stores list."""
    multi_site, _ = split_comparison(frame)
    if multi_site.empty:
        return pd.DataFrame(columns=COMPARISON_COLUMNS)

    rows: list[dict[str, object]] = []
    for _, record in multi_site.iterrows():
        best_price = _optional_int(record["best_price_yen"])
        spread = _optional_int(record["spread_yen"])
        spread = 0 if spread == "" else spread
        rate = round(spread / best_price, 6) if isinstance(best_price, int) and best_price else 0.0
        row = {
            "商品名": record["product_name_normalized"],
            "状態": _display_condition(record["condition"]),
            "最高値": best_price,
            "最高値の店": _store_label(record["best_site"]),
            "差率": rate,
            "差額": spread,
            "注意": CONDITION_INFERRED_LABEL if bool(record["condition_inferred"]) else "",
        }
        for label, column in zip(PRICE_COLUMN_LABELS, PRICE_SOURCE_COLUMNS):
            row[label] = _optional_int(record[column])
        rows.append(row)

    prepared = pd.DataFrame(rows, columns=COMPARISON_COLUMNS)
    # Sorted by rate so the products where the store choice actually matters
    # stay at the top, regardless of how expensive the box is.
    return prepared.sort_values(
        ["差率", "差額", "商品名", "状態"],
        ascending=[False, False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)


def _single_listing_sheet_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Build the 単独掲載 tab: rows only one store lists, so no spread exists."""
    _, single_site = split_comparison(frame)
    if single_site.empty:
        return pd.DataFrame(columns=SINGLE_LISTING_COLUMNS)

    rows = [
        {
            "商品名": record["product_name_normalized"],
            "状態": _display_condition(record["condition"]),
            "掲載店": _store_label(record["best_site"]),
            "買取価格": _optional_int(record["best_price_yen"]),
        }
        for _, record in single_site.iterrows()
    ]
    prepared = pd.DataFrame(rows, columns=SINGLE_LISTING_COLUMNS)
    return prepared.sort_values(
        ["買取価格", "商品名", "状態"],
        ascending=[False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)


def _raw_sheet_frame(frame: pd.DataFrame) -> pd.DataFrame:
    prepared = frame.rename(columns=RAW_HEADERS).copy()
    if "状態" in prepared:
        prepared["状態"] = prepared["状態"].map(_display_condition)
    return prepared


def _color(hex_color: str) -> dict[str, float]:
    return {
        "red": int(hex_color[0:2], 16) / 255,
        "green": int(hex_color[2:4], 16) / 255,
        "blue": int(hex_color[4:6], 16) / 255,
    }


def _grid_range(
    sheet_id: int,
    start_row: int,
    end_row: int,
    start_column: int,
    end_column: int,
) -> dict[str, object]:
    return {
        "sheetId": sheet_id,
        "startRowIndex": start_row,
        "endRowIndex": end_row,
        "startColumnIndex": start_column,
        "endColumnIndex": end_column,
    }


def _reset_format_request(sheet_id: int) -> dict[str, object]:
    # worksheet.clear() only removes values, so stale colours from a previous
    # run would otherwise stay behind on rows that no longer exist.
    return {
        "repeatCell": {
            "range": {"sheetId": sheet_id},
            "cell": {"userEnteredFormat": {}},
            "fields": "userEnteredFormat",
        }
    }


def _header_format_request(sheet_id: int, column_count: int) -> dict[str, object]:
    return {
        "repeatCell": {
            "range": _grid_range(sheet_id, 0, 1, 0, column_count),
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": _color(HEADER_BACKGROUND_HEX),
                    "textFormat": {"bold": True, "foregroundColor": _color("FFFFFF")},
                    "wrapStrategy": "WRAP",
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE",
                }
            },
            "fields": (
                "userEnteredFormat(backgroundColor,textFormat,wrapStrategy,"
                "horizontalAlignment,verticalAlignment)"
            ),
        }
    }


def _clip_request(sheet_id: int, row_count: int, column_count: int) -> dict[str, object]:
    return {
        "repeatCell": {
            "range": _grid_range(sheet_id, 1, row_count + 1, 0, column_count),
            "cell": {"userEnteredFormat": {"wrapStrategy": "CLIP"}},
            "fields": "userEnteredFormat.wrapStrategy",
        }
    }


def _number_format_request(
    sheet_id: int,
    row_count: int,
    start_column: int,
    end_column: int,
    number_type: str,
    pattern: str,
) -> dict[str, object]:
    return {
        "repeatCell": {
            "range": _grid_range(sheet_id, 1, row_count + 1, start_column, end_column),
            "cell": {
                "userEnteredFormat": {"numberFormat": {"type": number_type, "pattern": pattern}}
            },
            "fields": "userEnteredFormat.numberFormat",
        }
    }


def _row_runs(flags: list[bool]) -> list[tuple[int, int]]:
    """Collapse per-row flags into contiguous ranges to keep the batch small."""
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for index, flag in enumerate(flags):
        if flag and start is None:
            start = index
        elif not flag and start is not None:
            runs.append((start, index))
            start = None
    if start is not None:
        runs.append((start, len(flags)))
    return runs


def _background_requests(
    sheet_id: int, flags: list[bool], column: int, hex_color: str
) -> list[dict[str, object]]:
    return [
        {
            "repeatCell": {
                "range": _grid_range(sheet_id, start + 1, end + 1, column, column + 1),
                "cell": {"userEnteredFormat": {"backgroundColor": _color(hex_color)}},
                "fields": "userEnteredFormat.backgroundColor",
            }
        }
        for start, end in _row_runs(flags)
    ]


def _text_color_requests(
    sheet_id: int, flags: list[bool], column: int, hex_color: str
) -> list[dict[str, object]]:
    return [
        {
            "repeatCell": {
                "range": _grid_range(sheet_id, start + 1, end + 1, column, column + 1),
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"bold": True, "foregroundColor": _color(hex_color)}
                    }
                },
                "fields": "userEnteredFormat.textFormat",
            }
        }
        for start, end in _row_runs(flags)
    ]


def _column_width_requests(sheet_id: int, widths: list[int]) -> list[dict[str, object]]:
    return [
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": index,
                    "endIndex": index + 1,
                },
                "properties": {"pixelSize": width},
                "fields": "pixelSize",
            }
        }
        for index, width in enumerate(widths)
    ]


def _freeze_request(sheet_id: int, rows: int, columns: int) -> dict[str, object]:
    return {
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id,
                "gridProperties": {"frozenRowCount": rows, "frozenColumnCount": columns},
            },
            "fields": "gridProperties(frozenRowCount,frozenColumnCount)",
        }
    }


def _basic_filter_requests(
    sheet_id: int, row_count: int, column_count: int
) -> list[dict[str, object]]:
    return [
        {"clearBasicFilter": {"sheetId": sheet_id}},
        {
            "setBasicFilter": {
                "filter": {
                    "range": _grid_range(sheet_id, 0, row_count + 1, 0, column_count)
                }
            }
        },
    ]


def _comparison_format_requests(sheet_id: int, frame: pd.DataFrame) -> list[dict[str, object]]:
    column_count = len(COMPARISON_COLUMNS)
    row_count = len(frame)
    requests: list[dict[str, object]] = [
        _reset_format_request(sheet_id),
        _header_format_request(sheet_id, column_count),
        _freeze_request(sheet_id, rows=1, columns=2),
    ]
    requests += _column_width_requests(sheet_id, COMPARISON_COLUMN_WIDTHS)
    if row_count:
        best_prices = list(frame["最高値"])
        requests.append(_clip_request(sheet_id, row_count, column_count))
        requests.append(_number_format_request(sheet_id, row_count, 2, 3, "NUMBER", YEN_PATTERN))
        requests.append(_number_format_request(sheet_id, row_count, 5, 9, "NUMBER", YEN_PATTERN))
        requests.append(
            _number_format_request(sheet_id, row_count, 4, 5, "PERCENT", RATE_PATTERN)
        )
        for offset, label in enumerate(PRICE_COLUMN_LABELS):
            flags = [
                price != "" and best != "" and price == best
                for price, best in zip(frame[label], best_prices)
            ]
            requests += _background_requests(
                sheet_id, flags, 6 + offset, BEST_PRICE_BACKGROUND_HEX
            )
        high_spread = [
            isinstance(rate, (int, float)) and float(rate) >= HIGH_SPREAD_RATE
            for rate in frame["差率"]
        ]
        requests += _text_color_requests(sheet_id, high_spread, 4, HIGH_SPREAD_TEXT_HEX)
        warned = [str(value).strip() != "" for value in frame["注意"]]
        requests += _background_requests(sheet_id, warned, 9, WARNING_BACKGROUND_HEX)
    requests += _basic_filter_requests(sheet_id, row_count, column_count)
    return requests


def _single_listing_format_requests(
    sheet_id: int, frame: pd.DataFrame
) -> list[dict[str, object]]:
    column_count = len(SINGLE_LISTING_COLUMNS)
    row_count = len(frame)
    requests: list[dict[str, object]] = [
        _reset_format_request(sheet_id),
        _header_format_request(sheet_id, column_count),
        _freeze_request(sheet_id, rows=1, columns=0),
    ]
    requests += _column_width_requests(sheet_id, SINGLE_LISTING_COLUMN_WIDTHS)
    if row_count:
        requests.append(_clip_request(sheet_id, row_count, column_count))
        requests.append(_number_format_request(sheet_id, row_count, 3, 4, "NUMBER", YEN_PATTERN))
    requests += _basic_filter_requests(sheet_id, row_count, column_count)
    return requests


def _raw_format_requests(sheet_id: int, frame: pd.DataFrame) -> list[dict[str, object]]:
    column_count = max(len(frame.columns), 1)
    row_count = len(frame)
    requests: list[dict[str, object]] = [
        _reset_format_request(sheet_id),
        _header_format_request(sheet_id, column_count),
        _freeze_request(sheet_id, rows=1, columns=0),
    ]
    requests += _column_width_requests(sheet_id, RAW_COLUMN_WIDTHS[:column_count])
    if row_count:
        requests.append(_clip_request(sheet_id, row_count, column_count))
        price_start = list(frame.columns).index("買取価格") if "買取価格" in frame.columns else None
        if price_start is not None:
            requests.append(
                _number_format_request(
                    sheet_id, row_count, price_start, price_start + 3, "NUMBER", YEN_PATTERN
                )
            )
    requests += _basic_filter_requests(sheet_id, row_count, column_count)
    return requests


def _site_counts(comparison: pd.DataFrame) -> tuple[int, int, int]:
    if comparison.empty or "matched_site_count" not in comparison:
        return 0, 0, 0
    counts = comparison["matched_site_count"].value_counts()
    return int(counts.get(3, 0)), int(counts.get(2, 0)), int(counts.get(1, 0))


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
    three_site_count, two_site_count, single_site_count = _site_counts(comparison)
    return [
        timestamp,
        int(len(raw)),
        three_site_count + two_site_count,
        three_site_count,
        two_site_count,
        int(error_count),
        single_site_count,
    ]


def _ensure_summary_sheet(spreadsheet: object) -> None:
    try:
        summary = spreadsheet.worksheet(SUMMARY_SHEET_TITLE)
    except Exception as exc:
        # Avoid importing gspread exception classes in this helper.
        if exc.__class__.__name__ != "WorksheetNotFound":
            raise
        summary = spreadsheet.add_worksheet(title=SUMMARY_SHEET_TITLE, rows=30, cols=9)
    summary.update_acell("A1", "ポケカ買取価格表（手動更新）")
    # Counters are refreshed every run so the labels keep matching the tabs.
    summary.update(
        values=SUMMARY_COUNTER_ROWS,
        range_name=SUMMARY_COUNTER_RANGE,
        value_input_option="USER_ENTERED",
    )
    summary.update(
        values=SUMMARY_ERROR_ROW,
        range_name=SUMMARY_ERROR_RANGE,
        value_input_option="USER_ENTERED",
    )
    # Keep the smartphone update entry point even after future cloud refreshes.
    # Only the top-left cell is written because A9:B9 is merged in the live sheet.
    summary.update(
        values=[[MANUAL_UPDATE_FORMULA]],
        range_name="A9",
        value_input_option="USER_ENTERED",
    )


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
    sheet_plans = (
        (COMPARISON_SHEET_TITLE, _comparison_sheet_frame(comparison), _comparison_format_requests),
        (
            SINGLE_LISTING_SHEET_TITLE,
            _single_listing_sheet_frame(comparison),
            _single_listing_format_requests,
        ),
        (RAW_SHEET_TITLE, _raw_sheet_frame(raw), _raw_format_requests),
    )
    format_requests: list[dict[str, object]] = []
    previous_index: int | None = None
    for title, frame, build_requests in sheet_plans:
        needed_rows = max(len(frame) + 10, 100)
        needed_columns = max(len(frame.columns) + 2, 20)
        try:
            worksheet = spreadsheet.worksheet(title)
            worksheet.clear()
            if worksheet.row_count < needed_rows or worksheet.col_count < needed_columns:
                worksheet.resize(
                    rows=max(worksheet.row_count, needed_rows),
                    cols=max(worksheet.col_count, needed_columns),
                )
        except gspread.WorksheetNotFound:
            # Place a brand new tab right after the previous output tab so
            # 単独掲載 lands next to 比較 instead of at the end.
            worksheet = spreadsheet.add_worksheet(
                title=title,
                rows=needed_rows,
                cols=needed_columns,
                index=None if previous_index is None else previous_index + 1,
            )
        previous_index = worksheet.index
        values = _sheet_values(frame)
        worksheet.update(values=values, range_name="A1", value_input_option="RAW")
        format_requests += build_requests(worksheet.id, frame)
    if format_requests:
        spreadsheet.batch_update({"requests": format_requests})

    try:
        history = spreadsheet.worksheet(HISTORY_SHEET_TITLE)
        if history.col_count < len(HISTORY_HEADERS):
            history.resize(cols=len(HISTORY_HEADERS))
    except gspread.WorksheetNotFound:
        history = spreadsheet.add_worksheet(
            title=HISTORY_SHEET_TITLE, rows=1000, cols=len(HISTORY_HEADERS)
        )
    current_header = history.get_values("A1:G1")
    header_row = current_header[0] if current_header else []
    if header_row[: len(HISTORY_HEADERS)] != HISTORY_HEADERS:
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
