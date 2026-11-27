from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from .catalog import box_msrp_yen, box_series_label
from .collectors.collect_sheet import SPREADSHEET_ID as COLLECT_SOURCE_SPREADSHEET_ID
from .market_analysis import analyze_market
from .normalize import normalize_product_name
from .prompt_builder import (
    PROMPT_SHEET_HEADERS,
    TOOL_SITE_BASE_URL,
    PromptBundle,
    build_prompt_bundle,
    write_prompt_outputs,
)
from .stores import (
    ALL_SOURCE_ORDER,
    DEFAULT_SOURCES,
    SOURCE_LABELS,
    STORE_BY_CODE,
    STORE_REGISTRY,
)
from .web_export import write_web_market_json


LOGGER = logging.getLogger(__name__)


SPREADSHEET_TITLE = "ポケカ買取価格表"

SOURCE_ORDER = ALL_SOURCE_ORDER
PRICE_COLUMN_LABELS = [SOURCE_LABELS[code] for code in DEFAULT_SOURCES]
PRICE_SOURCE_COLUMNS = [f"{code}_price_yen" for code in DEFAULT_SOURCES]

COMPARISON_LEADING_COLUMNS = [
    "シリーズ",
    "商品名",
    "最高値",
    "前回比",
    "最高値の店",
    "差率",
    "差額",
    "定価比",
]
COMPARISON_TRAILING_COLUMNS = ["注意"]

# Default 比較 columns (active store columns expand/contract dynamically from fetched data).
COMPARISON_COLUMNS = (
    COMPARISON_LEADING_COLUMNS + PRICE_COLUMN_LABELS + COMPARISON_TRAILING_COLUMNS
)
COMPARISON_REQUIRED_COLUMNS = [
    "product_name_normalized",
    "condition",
    "condition_inferred",
    "best_site",
    "best_price_yen",
    "spread_yen",
    "matched_site_count",
]
COMPARISON_SOURCE_COLUMNS = COMPARISON_REQUIRED_COLUMNS + PRICE_SOURCE_COLUMNS

NO_SHRINK_LEADING_COLUMNS = [
    "シリーズ",
    "商品名",
    "シュリンク無最高値",
    "最高値の店",
    "シュリンク有最高値",
    "有無差額",
    "有無差率",
]
NO_SHRINK_DEFAULT_STORES = ("homura", "runto")
NO_SHRINK_COLUMNS = NO_SHRINK_LEADING_COLUMNS + [
    SOURCE_LABELS[code] for code in NO_SHRINK_DEFAULT_STORES
]

SINGLE_LISTING_COLUMNS = ["シリーズ", "商品名", "状態", "掲載店", "買取価格"]
STORE_GUIDE_COLUMNS = [
    "店舗名",
    "取得状態",
    "今回取得件数",
    "送料条件",
    "価格保証",
    "振込手数料",
    "入金目安",
    "シュリンク無",
    "特徴・注意点",
    "公式価格表URL",
]

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

SUMMARY_SHEET_TITLE = "サマリー"
COMPARISON_SHEET_TITLE = "比較"
NO_SHRINK_SHEET_TITLE = "シュリンク無比較"
TREND_SHEET_TITLE = "価格推移（シュリンク有）"
SINGLE_LISTING_SHEET_TITLE = "単独掲載"
STORE_GUIDE_SHEET_TITLE = "店舗条件"
HISTORY_SHEET_TITLE = "更新履歴"
RAW_SHEET_TITLE = "全取得"
PROMPT_SHEET_TITLE = "発信プロンプト"
TREND_ARCHIVE_SHEET_TITLE = "推移データ（保管用）"

TREND_HEADERS = ["日付", "商品名", "最高値", "最高値の店"]
TREND_FIXED_COLUMNS = ["商品名", "最新最高値", "最高値の店", "前回比", "7日前比", "30日推移"]
TREND_FIXED_COLUMN_WIDTHS = [260, 105, 135, 90, 90, 130]
TREND_DATE_COLUMN_WIDTH = 80
TREND_WINDOW_DATES = 30
TREND_ACTIVE_RECENCY_DAYS = 14

HISTORY_HEADERS = [
    "実行日時",
    "全取得レコード",
    "比較行（2サイト以上）",
    "3サイト以上一致",
    "2サイト一致",
    "取得エラー",
    "1サイトのみ",
]
HISTORY_COLUMN_WIDTHS = [150, 120, 155, 125, 110, 100, 115]
MAX_HISTORY_ROWS = 365

JAPAN_TIME_ZONE = timezone(timedelta(hours=9), name="JST")
MANUAL_UPDATE_URL = "https://pokeca-price-update.vercel.app"
MANUAL_UPDATE_FORMULA = f'=HYPERLINK("{MANUAL_UPDATE_URL}","🔄 価格表を手動更新")'

SUMMARY_COUNTER_RANGE = "A3"
REMOVED_SUMMARY_SOURCES = {"買取マッチョ"}


def _latest_history_value(column: str) -> str:
    """Expression for one column of the newest history row, without the '='.

    The previous LOOKUP(2,1/(range<>"")) idiom needs its search vector sorted
    and fills the rest of the column with errors, and it was resolving to the
    header row, so every counter showed a column name instead of a number.
    Matching the newest timestamp instead ties every counter to the same row
    that 最終更新 reports.
    """
    return (
        f"IFERROR(INDEX(更新履歴!{column}:{column},"
        "MATCH(MAX(更新履歴!A2:A),更新履歴!A:A,0)),0)"
    )


# Row 9 holds the merged manual update link and rows 10 and below hold hand
# written content, so everything this function writes has to fit in A3:B8.
SUMMARY_COUNTER_ROWS = [
    ["最終更新", '=IFERROR(MAX(更新履歴!A2:A),"")'],
    ["全取得レコード", "=" + _latest_history_value("B")],
    ["BOX比較件数（2サイト以上）", "=" + _latest_history_value("C")],
    [
        "内訳（3サイト以上／2サイト）",
        f'={_latest_history_value("D")}&" / "&{_latest_history_value("E")}',
    ],
    ["1サイトのみ（単独掲載）", "=" + _latest_history_value("G")],
    ["取得エラー", "=" + _latest_history_value("F")],
]
SUMMARY_COUNTER_LIMIT = 6

HIGH_SPREAD_RATE = 0.05
# A 3.7% gap on a 135,000 yen box still hands over more money than a 32% gap on
# an 11,800 yen box, so the yen column carries its own threshold.
HIGH_SPREAD_YEN = 3_000
YEN_PATTERN = "¥#,##0"
SIGNED_YEN_PATTERN = '+¥#,##0;-¥#,##0;"±0"'
INTEGER_PATTERN = "#,##0"
DATETIME_PATTERN = "yyyy-mm-dd hh:mm"
RATE_PATTERN = "0.0%"
RATIO_PATTERN = '0.0"倍"'

HEADER_BACKGROUND_HEX = "1F3864"
ZEBRA_BACKGROUND_HEX = "F7F9FC"
BEST_PRICE_BACKGROUND_HEX = "C6EFCE"
WARNING_BACKGROUND_HEX = "FFF2CC"
HIGH_SPREAD_TEXT_HEX = "C00000"
HIGH_SPREAD_YEN_TEXT_HEX = "BF8F00"
UP_PRICE_TEXT_HEX = "137333"
DOWN_PRICE_TEXT_HEX = "1967D2"
FLAT_PRICE_TEXT_HEX = "80868B"

COMPARISON_HEADER_NOTES_BY_NAME = {
    "前回比": "前回比 ＝ 前日以前の直近記録（シュリンク有の最高値）との差額。上昇は緑、下落は青で表示します。",
    "差率": "差率 ＝ 差額 ÷ 最高値。5%以上は赤太字。表はこの列の降順です。",
    "差額": "差額 ＝ 最高値 － 最安値。3,000円以上は金色の太字。率が低くても手取りの差が大きい商品を見落とさないための印です。",
    "定価比": "定価比 ＝ 最高値 ÷ 公式BOX定価（税込）。1.0倍に近いほど定価付近の底値圏、高いほどプレミア相場です。",
    "注意": (
        "片方の店舗だけ状態の記載がない場合、同名商品の状態を当てはめて比較しています（状態推定）。"
        "元の商品名・送料や価格保証条件は「店舗条件」「全取得」タブで確認できます。"
    ),
}
# Kept for backwards compatibility with callers/tests inspecting default column indices.
COMPARISON_HEADER_NOTES = {
    COMPARISON_COLUMNS.index(name): note
    for name, note in COMPARISON_HEADER_NOTES_BY_NAME.items()
}
NO_SHRINK_HEADER_NOTES_BY_NAME = {
    "有無差額": "有無差額 ＝ 同名BOXのシュリンク有最高値 － シュリンク無最高値。シュリンク無による相場ペナルティ額です。",
    "有無差率": "有無差率 ＝ 有無差額 ÷ シュリンク有最高値。率が小さいBOXほどシュリンク無でも高く売れやすい傾向があります。",
}
TREND_HEADER_NOTES = {
    1: "シュリンク有と明記された買取価格の最新最高値です（状態不明の価格は含みません）。",
    3: "直近の最高値と、その1回前の記録との差額。上昇は緑、下落は青で表示します。",
    4: "直近の記録日から7日以上前の最新記録との差額。7日分の履歴がない新商品は空欄になります。",
    5: (
        "直近最大30回分の価格推移ミニグラフ（左＝古い日付 → 右＝新しい日付）。"
        f"全期間の履歴は非表示シート「{TREND_ARCHIVE_SHEET_TITLE}」に自動保存されています。"
    ),
}

PROMPT_HEADER_NOTES = {
    3: (
        "この列のセルを1回選択してコピーし、無料/Web版のChatGPT・Gemini・Claudeへそのまま貼り付けて使えます"
        "（APIキー課金不要）。特定店舗名や店舗別の生価格表は自動除外済みです。"
    ),
    4: "誘導先の無料計算ツール「トレカ損益ラボ」URLや収益導線（note・ASP）のメモです。ASP案内時は必ず #PR 表記を入れてください。",
}
PROMPT_CATEGORY_ACCENT_HEX = "E8F0FE"

COMPARISON_COLUMN_WIDTHS_BY_NAME = {
    "シリーズ": 95,
    "商品名": 250,
    "最高値": 95,
    "前回比": 90,
    "最高値の店": 135,
    "差率": 70,
    "差額": 90,
    "定価比": 72,
    "注意": 80,
}
STORE_PRICE_COLUMN_WIDTH = 95
NO_SHRINK_COLUMN_WIDTHS_BY_NAME = {
    "シリーズ": 95,
    "商品名": 250,
    "シュリンク無最高値": 115,
    "最高値の店": 130,
    "シュリンク有最高値": 115,
    "有無差額": 95,
    "有無差率": 78,
}
SINGLE_LISTING_COLUMN_WIDTHS = [95, 290, 100, 125, 110]
STORE_GUIDE_COLUMN_WIDTHS = [115, 85, 95, 210, 210, 165, 185, 85, 270, 240]
RAW_COLUMN_WIDTHS = [80, 300, 220, 220, 110, 100, 100, 100, 100, 100, 90, 220, 120, 150, 150]
PROMPT_COLUMN_WIDTHS = [115, 215, 220, 680, 255]


def _sheet_values(frame: pd.DataFrame) -> list[list[object]]:
    cleaned = frame.astype(object).where(pd.notna(frame), "")
    return [list(frame.columns)] + cleaned.values.tolist()


def _column_letter(index_zero_based: int) -> str:
    """Convert a 0-based column index into an A1 column label (0 -> A, 26 -> AA)."""
    value = index_zero_based + 1
    letters: list[str] = []
    while value > 0:
        value, remainder = divmod(value - 1, 26)
        letters.append(chr(ord("A") + remainder))
    return "".join(reversed(letters))


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
    if len(sources) >= 3:
        return f"{len(sources)}店同額"
    return "・".join(SOURCE_LABELS.get(source, source) for source in sources)


def _has_comparison_columns(frame: pd.DataFrame) -> bool:
    return not frame.empty and set(COMPARISON_REQUIRED_COLUMNS).issubset(frame.columns)


def _active_store_codes(frame: pd.DataFrame, *, fallback: tuple[str, ...] = DEFAULT_SOURCES) -> list[str]:
    """Select store columns that actually contain at least one price in this comparison frame."""
    if frame.empty:
        return list(fallback)
    active = [
        code
        for code in SOURCE_ORDER
        if f"{code}_price_yen" in frame.columns and frame[f"{code}_price_yen"].notna().any()
    ]
    return active if active else list(fallback)


def split_comparison(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split the comparison result into "two or more stores" and "single store"."""
    if not _has_comparison_columns(frame):
        empty = frame.iloc[0:0] if isinstance(frame, pd.DataFrame) else pd.DataFrame()
        return empty.copy(), empty.copy()
    counts = pd.to_numeric(frame["matched_site_count"], errors="coerce").fillna(0)
    return frame[counts >= 2].copy(), frame[counts == 1].copy()


def _comparison_sheet_frame(
    frame: pd.DataFrame,
    *,
    previous_prices: dict[str, int] | None = None,
) -> pd.DataFrame:
    """Build the 比較 tab from shrink-wrapped rows listed by two or more stores."""
    multi_site, _ = split_comparison(frame)
    if not multi_site.empty:
        multi_site = multi_site[multi_site["condition"] == "shrink_wrapped"].copy()
    if multi_site.empty:
        return pd.DataFrame(columns=COMPARISON_COLUMNS)

    active_codes = _active_store_codes(multi_site, fallback=DEFAULT_SOURCES)
    active_labels = [SOURCE_LABELS[code] for code in active_codes]
    columns = COMPARISON_LEADING_COLUMNS + active_labels + COMPARISON_TRAILING_COLUMNS

    rows: list[dict[str, object]] = []
    for _, record in multi_site.iterrows():
        name = str(record["product_name_normalized"])
        best_price = _optional_int(record["best_price_yen"])
        prev_diff: object = ""
        if (
            previous_prices
            and isinstance(best_price, int)
            and name in previous_prices
        ):
            prev_diff = best_price - previous_prices[name]
        spread = _optional_int(record["spread_yen"])
        spread = 0 if spread == "" else spread
        rate = round(spread / best_price, 6) if isinstance(best_price, int) and best_price else 0.0
        msrp = box_msrp_yen(name)
        msrp_ratio: object = (
            round(best_price / msrp, 2)
            if isinstance(best_price, int) and msrp and msrp > 0
            else ""
        )
        row: dict[str, object] = {
            "シリーズ": box_series_label(name),
            "商品名": name,
            "最高値": best_price,
            "前回比": prev_diff,
            "最高値の店": _store_label(record["best_site"]),
            "差率": rate,
            "差額": spread,
            "定価比": msrp_ratio,
            "注意": CONDITION_INFERRED_LABEL if bool(record["condition_inferred"]) else "",
        }
        for code, label in zip(active_codes, active_labels):
            row[label] = _optional_int(record.get(f"{code}_price_yen"))
        rows.append(row)

    prepared = pd.DataFrame(rows, columns=columns)
    # Sorted by rate so the products where the store choice actually matters
    # stay at the top, regardless of how expensive the box is.
    return prepared.sort_values(
        ["差率", "差額", "最高値", "商品名"],
        ascending=[False, False, False, True],
        kind="mergesort",
    ).reset_index(drop=True)


def _no_shrink_sheet_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Build the シュリンク無比較 tab showing no-shrink store comparison & shrink penalty."""
    if not _has_comparison_columns(frame):
        return pd.DataFrame(columns=NO_SHRINK_COLUMNS)

    no_shrink = frame[
        (frame["condition"] == "no_shrink") & frame["best_price_yen"].notna()
    ].copy()
    if no_shrink.empty:
        return pd.DataFrame(columns=NO_SHRINK_COLUMNS)

    shrink_best_map: dict[str, int] = {}
    shrink_rows = frame[
        (frame["condition"] == "shrink_wrapped") & frame["best_price_yen"].notna()
    ]
    for _, record in shrink_rows.iterrows():
        best_val = _optional_int(record["best_price_yen"])
        if isinstance(best_val, int):
            shrink_best_map[str(record["product_name_normalized"])] = best_val

    active_codes = _active_store_codes(no_shrink, fallback=NO_SHRINK_DEFAULT_STORES)
    active_labels = [SOURCE_LABELS[code] for code in active_codes]
    columns = NO_SHRINK_LEADING_COLUMNS + active_labels

    rows: list[dict[str, object]] = []
    for _, record in no_shrink.iterrows():
        name = str(record["product_name_normalized"])
        ns_best = _optional_int(record["best_price_yen"])
        shrink_best: object = shrink_best_map.get(name, "")
        gap_yen: object = ""
        gap_rate: object = ""
        if isinstance(ns_best, int) and isinstance(shrink_best, int) and shrink_best > 0:
            gap_yen = shrink_best - ns_best
            gap_rate = round(gap_yen / shrink_best, 6)
        row: dict[str, object] = {
            "シリーズ": box_series_label(name),
            "商品名": name,
            "シュリンク無最高値": ns_best,
            "最高値の店": _store_label(record["best_site"]),
            "シュリンク有最高値": shrink_best,
            "有無差額": gap_yen,
            "有無差率": gap_rate,
        }
        for code, label in zip(active_codes, active_labels):
            row[label] = _optional_int(record.get(f"{code}_price_yen"))
        rows.append(row)

    prepared = pd.DataFrame(rows, columns=columns)
    return prepared.sort_values(
        ["シュリンク無最高値", "商品名"],
        ascending=[False, True],
        kind="mergesort",
    ).reset_index(drop=True)


def _single_listing_sheet_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Build the 単独掲載 tab: rows only one store lists, so no spread exists."""
    _, single_site = split_comparison(frame)
    if single_site.empty:
        return pd.DataFrame(columns=SINGLE_LISTING_COLUMNS)

    rows = [
        {
            "シリーズ": box_series_label(str(record["product_name_normalized"])),
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


def _store_guide_sheet_frame(raw: pd.DataFrame) -> pd.DataFrame:
    """Build the 店舗条件 tab summarizing shipping, price-lock, fee, and live record counts."""
    counts: dict[str, int] = {}
    if raw is not None and not raw.empty and "source" in raw.columns:
        counts = {str(k): int(v) for k, v in raw.groupby("source").size().items()}

    rows: list[dict[str, object]] = []
    for store in STORE_REGISTRY:
        fetched_count = counts.get(store.code, 0)
        if fetched_count > 0:
            status_label = "稼働中"
        elif store.default_enabled:
            status_label = "未取得"
        else:
            status_label = "一時中断"
        rows.append(
            {
                "店舗名": store.label,
                "取得状態": status_label,
                "今回取得件数": fetched_count,
                "送料条件": store.shipping_rule,
                "価格保証": store.price_lock_rule,
                "振込手数料": store.transfer_fee,
                "入金目安": store.payout_speed,
                "シュリンク無": "○" if store.no_shrink_supported else "×",
                "特徴・注意点": store.notes,
                "公式価格表URL": store.url,
            }
        )
    return pd.DataFrame(rows, columns=STORE_GUIDE_COLUMNS)


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
            "cell": {
                "userEnteredFormat": {
                    "wrapStrategy": "CLIP",
                    "verticalAlignment": "MIDDLE",
                }
            },
            "fields": "userEnteredFormat(wrapStrategy,verticalAlignment)",
        }
    }


def _alignment_request(
    sheet_id: int,
    row_count: int,
    start_column: int,
    end_column: int,
    alignment: str,
) -> dict[str, object]:
    return {
        "repeatCell": {
            "range": _grid_range(sheet_id, 1, row_count + 1, start_column, end_column),
            "cell": {"userEnteredFormat": {"horizontalAlignment": alignment}},
            "fields": "userEnteredFormat.horizontalAlignment",
        }
    }


def _row_height_requests(
    sheet_id: int, row_count: int, *, header_px: int = 34, data_px: int = 28
) -> list[dict[str, object]]:
    requests: list[dict[str, object]] = [
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "ROWS",
                    "startIndex": 0,
                    "endIndex": 1,
                },
                "properties": {"pixelSize": header_px},
                "fields": "pixelSize",
            }
        }
    ]
    if row_count > 0:
        requests.append(
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": 1,
                        "endIndex": row_count + 1,
                    },
                    "properties": {"pixelSize": data_px},
                    "fields": "pixelSize",
                }
            }
        )
    return requests


def _zebra_requests(sheet_id: int, row_count: int, column_count: int) -> list[dict[str, object]]:
    return [
        {
            "repeatCell": {
                "range": _grid_range(sheet_id, row_index + 1, row_index + 2, 0, column_count),
                "cell": {"userEnteredFormat": {"backgroundColor": _color(ZEBRA_BACKGROUND_HEX)}},
                "fields": "userEnteredFormat.backgroundColor",
            }
        }
        for row_index in range(row_count)
        if row_index % 2 == 1
    ]


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
    sheet_id: int,
    flags: list[bool],
    column: int,
    hex_color: str,
    *,
    bold: bool = True,
) -> list[dict[str, object]]:
    return [
        {
            "repeatCell": {
                "range": _grid_range(sheet_id, start + 1, end + 1, column, column + 1),
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"bold": bold, "foregroundColor": _color(hex_color)}
                    }
                },
                "fields": "userEnteredFormat.textFormat",
            }
        }
        for start, end in _row_runs(flags)
    ]


def _delta_text_color_requests(
    sheet_id: int, values: list[object], column: int
) -> list[dict[str, object]]:
    up_flags = [isinstance(val, (int, float)) and val > 0 for val in values]
    down_flags = [isinstance(val, (int, float)) and val < 0 for val in values]
    flat_flags = [isinstance(val, (int, float)) and val == 0 for val in values]
    return (
        _text_color_requests(sheet_id, up_flags, column, UP_PRICE_TEXT_HEX, bold=True)
        + _text_color_requests(sheet_id, down_flags, column, DOWN_PRICE_TEXT_HEX, bold=True)
        + _text_color_requests(sheet_id, flat_flags, column, FLAT_PRICE_TEXT_HEX, bold=False)
    )


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


def _note_request(sheet_id: int, row: int, column: int, note: str) -> dict[str, object]:
    """Explain a column without spending header width on the explanation."""
    return {
        "updateCells": {
            "range": _grid_range(sheet_id, row, row + 1, column, column + 1),
            "rows": [{"values": [{"note": note}]}],
            "fields": "note",
        }
    }


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
    columns = list(frame.columns) if len(frame.columns) else list(COMPARISON_COLUMNS)
    column_count = len(columns)
    row_count = len(frame)
    col_index = {name: idx for idx, name in enumerate(columns)}
    widths = [
        COMPARISON_COLUMN_WIDTHS_BY_NAME.get(name, STORE_PRICE_COLUMN_WIDTH)
        for name in columns
    ]
    store_label_set = set(SOURCE_LABELS.values())
    store_columns = [name for name in columns if name in store_label_set]

    requests: list[dict[str, object]] = [
        _reset_format_request(sheet_id),
        _header_format_request(sheet_id, column_count),
        _freeze_request(sheet_id, rows=1, columns=2),
    ]
    requests += _row_height_requests(sheet_id, row_count)
    requests += [
        _note_request(sheet_id, 0, col_index[name], note)
        for name, note in COMPARISON_HEADER_NOTES_BY_NAME.items()
        if name in col_index
    ]
    requests += _column_width_requests(sheet_id, widths)
    if row_count:
        best_prices = list(frame["最高値"])
        requests.append(_clip_request(sheet_id, row_count, column_count))
        requests += _zebra_requests(sheet_id, row_count, column_count)
        for name in ("シリーズ", "注意"):
            if name in col_index:
                idx = col_index[name]
                requests.append(_alignment_request(sheet_id, row_count, idx, idx + 1, "CENTER"))
        right_columns = ["最高値", "前回比", "差率", "差額", "定価比"] + store_columns
        for name in right_columns:
            if name in col_index:
                idx = col_index[name]
                requests.append(_alignment_request(sheet_id, row_count, idx, idx + 1, "RIGHT"))
        for name in ["最高値", "差額"] + store_columns:
            if name in col_index:
                idx = col_index[name]
                requests.append(
                    _number_format_request(sheet_id, row_count, idx, idx + 1, "NUMBER", YEN_PATTERN)
                )
        if "前回比" in col_index:
            idx = col_index["前回比"]
            requests.append(
                _number_format_request(
                    sheet_id, row_count, idx, idx + 1, "NUMBER", SIGNED_YEN_PATTERN
                )
            )
            requests += _delta_text_color_requests(sheet_id, list(frame["前回比"]), idx)
        if "差率" in col_index:
            idx = col_index["差率"]
            requests.append(
                _number_format_request(sheet_id, row_count, idx, idx + 1, "PERCENT", RATE_PATTERN)
            )
            high_spread = [
                isinstance(rate, (int, float)) and float(rate) >= HIGH_SPREAD_RATE
                for rate in frame["差率"]
            ]
            requests += _text_color_requests(sheet_id, high_spread, idx, HIGH_SPREAD_TEXT_HEX)
        if "差額" in col_index:
            idx = col_index["差額"]
            large_spread = [
                isinstance(amount, (int, float)) and float(amount) >= HIGH_SPREAD_YEN
                for amount in frame["差額"]
            ]
            requests += _text_color_requests(sheet_id, large_spread, idx, HIGH_SPREAD_YEN_TEXT_HEX)
        if "定価比" in col_index:
            idx = col_index["定価比"]
            requests.append(
                _number_format_request(sheet_id, row_count, idx, idx + 1, "NUMBER", RATIO_PATTERN)
            )
        for label in store_columns:
            idx = col_index[label]
            flags = [
                price != "" and best != "" and price == best
                for price, best in zip(frame[label], best_prices)
            ]
            requests += _background_requests(sheet_id, flags, idx, BEST_PRICE_BACKGROUND_HEX)
        if "注意" in col_index:
            idx = col_index["注意"]
            warned = [str(value).strip() != "" for value in frame["注意"]]
            requests += _background_requests(sheet_id, warned, idx, WARNING_BACKGROUND_HEX)
    requests += _basic_filter_requests(sheet_id, row_count, column_count)
    return requests


def _no_shrink_format_requests(sheet_id: int, frame: pd.DataFrame) -> list[dict[str, object]]:
    columns = list(frame.columns) if len(frame.columns) else list(NO_SHRINK_COLUMNS)
    column_count = len(columns)
    row_count = len(frame)
    col_index = {name: idx for idx, name in enumerate(columns)}
    widths = [
        NO_SHRINK_COLUMN_WIDTHS_BY_NAME.get(name, STORE_PRICE_COLUMN_WIDTH)
        for name in columns
    ]
    store_label_set = set(SOURCE_LABELS.values())
    store_columns = [name for name in columns if name in store_label_set]

    requests: list[dict[str, object]] = [
        _reset_format_request(sheet_id),
        _header_format_request(sheet_id, column_count),
        _freeze_request(sheet_id, rows=1, columns=2),
    ]
    requests += _row_height_requests(sheet_id, row_count)
    requests += [
        _note_request(sheet_id, 0, col_index[name], note)
        for name, note in NO_SHRINK_HEADER_NOTES_BY_NAME.items()
        if name in col_index
    ]
    requests += _column_width_requests(sheet_id, widths)
    if row_count:
        best_prices = list(frame["シュリンク無最高値"])
        requests.append(_clip_request(sheet_id, row_count, column_count))
        requests += _zebra_requests(sheet_id, row_count, column_count)
        if "シリーズ" in col_index:
            idx = col_index["シリーズ"]
            requests.append(_alignment_request(sheet_id, row_count, idx, idx + 1, "CENTER"))
        for name in ["シュリンク無最高値", "シュリンク有最高値", "有無差額", "有無差率"] + store_columns:
            if name in col_index:
                idx = col_index[name]
                requests.append(_alignment_request(sheet_id, row_count, idx, idx + 1, "RIGHT"))
        for name in ["シュリンク無最高値", "シュリンク有最高値", "有無差額"] + store_columns:
            if name in col_index:
                idx = col_index[name]
                requests.append(
                    _number_format_request(sheet_id, row_count, idx, idx + 1, "NUMBER", YEN_PATTERN)
                )
        if "有無差率" in col_index:
            idx = col_index["有無差率"]
            requests.append(
                _number_format_request(sheet_id, row_count, idx, idx + 1, "PERCENT", RATE_PATTERN)
            )
        for label in store_columns:
            idx = col_index[label]
            flags = [
                price != "" and best != "" and price == best
                for price, best in zip(frame[label], best_prices)
            ]
            requests += _background_requests(sheet_id, flags, idx, BEST_PRICE_BACKGROUND_HEX)
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
        _freeze_request(sheet_id, rows=1, columns=2),
    ]
    requests += _row_height_requests(sheet_id, row_count)
    requests += _column_width_requests(sheet_id, SINGLE_LISTING_COLUMN_WIDTHS)
    if row_count:
        requests.append(_clip_request(sheet_id, row_count, column_count))
        requests += _zebra_requests(sheet_id, row_count, column_count)
        requests.append(_alignment_request(sheet_id, row_count, 0, 1, "CENTER"))
        requests.append(_alignment_request(sheet_id, row_count, 2, 3, "CENTER"))
        requests.append(_alignment_request(sheet_id, row_count, 4, 5, "RIGHT"))
        requests.append(_number_format_request(sheet_id, row_count, 4, 5, "NUMBER", YEN_PATTERN))
    requests += _basic_filter_requests(sheet_id, row_count, column_count)
    return requests


def _store_guide_format_requests(sheet_id: int, frame: pd.DataFrame) -> list[dict[str, object]]:
    column_count = len(STORE_GUIDE_COLUMNS)
    row_count = len(frame)
    requests: list[dict[str, object]] = [
        _reset_format_request(sheet_id),
        _header_format_request(sheet_id, column_count),
        _freeze_request(sheet_id, rows=1, columns=1),
    ]
    requests += _row_height_requests(sheet_id, row_count, header_px=34, data_px=46)
    requests += _column_width_requests(sheet_id, STORE_GUIDE_COLUMN_WIDTHS)
    if row_count:
        requests.append(
            {
                "repeatCell": {
                    "range": _grid_range(sheet_id, 1, row_count + 1, 0, column_count),
                    "cell": {
                        "userEnteredFormat": {
                            "wrapStrategy": "WRAP",
                            "verticalAlignment": "MIDDLE",
                        }
                    },
                    "fields": "userEnteredFormat(wrapStrategy,verticalAlignment)",
                }
            }
        )
        requests += _zebra_requests(sheet_id, row_count, column_count)
        requests.append(_alignment_request(sheet_id, row_count, 1, 2, "CENTER"))
        requests.append(_alignment_request(sheet_id, row_count, 2, 3, "RIGHT"))
        requests.append(_alignment_request(sheet_id, row_count, 7, 8, "CENTER"))
        requests.append(
            _number_format_request(sheet_id, row_count, 2, 3, "NUMBER", INTEGER_PATTERN)
        )
        statuses = [str(v) for v in frame["取得状態"]]
        requests += _text_color_requests(
            sheet_id, [s == "稼働中" for s in statuses], 1, UP_PRICE_TEXT_HEX, bold=True
        )
        requests += _text_color_requests(
            sheet_id, [s == "未取得" for s in statuses], 1, HIGH_SPREAD_TEXT_HEX, bold=True
        )
        requests += _text_color_requests(
            sheet_id, [s == "一時中断" for s in statuses], 1, FLAT_PRICE_TEXT_HEX, bold=False
        )
    return requests


def _raw_format_requests(sheet_id: int, frame: pd.DataFrame) -> list[dict[str, object]]:
    column_count = max(len(frame.columns), 1)
    row_count = len(frame)
    requests: list[dict[str, object]] = [
        _reset_format_request(sheet_id),
        _header_format_request(sheet_id, column_count),
        _freeze_request(sheet_id, rows=1, columns=0),
    ]
    requests += _row_height_requests(sheet_id, row_count, header_px=32, data_px=24)
    requests += _column_width_requests(sheet_id, RAW_COLUMN_WIDTHS[:column_count])
    if row_count:
        requests.append(_clip_request(sheet_id, row_count, column_count))
        requests += _zebra_requests(sheet_id, row_count, column_count)
        price_start = list(frame.columns).index("買取価格") if "買取価格" in frame.columns else None
        if price_start is not None:
            requests.append(
                _number_format_request(
                    sheet_id, row_count, price_start, price_start + 3, "NUMBER", YEN_PATTERN
                )
            )
    requests += _basic_filter_requests(sheet_id, row_count, column_count)
    return requests


def _history_format_requests(
    sheet_id: int, rows: list[list[object]]
) -> list[dict[str, object]]:
    column_count = len(HISTORY_HEADERS)
    row_count = len(rows)
    requests: list[dict[str, object]] = [
        _reset_format_request(sheet_id),
        _header_format_request(sheet_id, column_count),
        _freeze_request(sheet_id, rows=1, columns=0),
    ]
    requests += _row_height_requests(sheet_id, row_count, header_px=32, data_px=26)
    requests += _column_width_requests(sheet_id, HISTORY_COLUMN_WIDTHS)
    if row_count:
        requests.append(_clip_request(sheet_id, row_count, column_count))
        requests += _zebra_requests(sheet_id, row_count, column_count)
        requests.append(_alignment_request(sheet_id, row_count, 0, 1, "CENTER"))
        requests.append(_alignment_request(sheet_id, row_count, 1, column_count, "RIGHT"))
        requests.append(
            _number_format_request(sheet_id, row_count, 0, 1, "DATE_TIME", DATETIME_PATTERN)
        )
        requests.append(
            _number_format_request(
                sheet_id, row_count, 1, column_count, "NUMBER", INTEGER_PATTERN
            )
        )
        error_flags = [
            len(row) > 5 and isinstance(row[5], (int, float)) and row[5] > 0 for row in rows
        ]
        requests += _text_color_requests(sheet_id, error_flags, 5, HIGH_SPREAD_TEXT_HEX)
    requests += _basic_filter_requests(sheet_id, row_count, column_count)
    return requests


def _site_counts(comparison: pd.DataFrame) -> tuple[int, int, int]:
    if comparison.empty or "matched_site_count" not in comparison:
        return 0, 0, 0
    counts = pd.to_numeric(comparison["matched_site_count"], errors="coerce").fillna(0)
    return (
        int((counts >= 3).sum()),
        int((counts == 2).sum()),
        int((counts == 1).sum()),
    )


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


def _history_backfill_updates(rows: list[list[object]]) -> list[dict[str, object]]:
    """Restate history rows written before the 1サイトのみ column existed.

    Older rows recorded every comparison row in C, including the single-store
    ones, so C means something different from the rows written today. The old
    rows already carry the 3-site and 2-site counts, so both new values follow
    from the row itself and no scraped snapshot is needed.
    """
    updates: list[dict[str, object]] = []
    for offset, row in enumerate(rows):
        row_number = offset + 2
        if not row or not str(row[0]).strip():
            continue
        if len(row) >= 7 and str(row[6]).strip():
            continue
        try:
            total = int(str(row[2]).replace(",", ""))
            three_site_count = int(str(row[3]).replace(",", ""))
            two_site_count = int(str(row[4]).replace(",", ""))
        except (IndexError, ValueError):
            continue
        single_site_count = total - three_site_count - two_site_count
        if single_site_count < 0:
            continue
        updates.append(
            {"range": f"C{row_number}", "values": [[three_site_count + two_site_count]]}
        )
        updates.append({"range": f"G{row_number}", "values": [[single_site_count]]})
    return updates


def _coerce_history_cell(value: object) -> object:
    text = str(value).strip().replace(",", "")
    if text == "":
        return ""
    try:
        return int(float(text))
    except ValueError:
        return value


def _history_sort_key(row: list[object]) -> pd.Timestamp:
    parsed = pd.to_datetime(str(row[0]).strip(), errors="coerce")
    if pd.isna(parsed):
        return pd.Timestamp.min
    return parsed


def _prepare_history_rows(
    existing_rows: list[list[object]],
    new_row: list[object],
    *,
    max_rows: int = MAX_HISTORY_ROWS,
) -> list[list[object]]:
    """Normalize legacy history rows, append the newest run, and sort newest-first."""
    normalized_existing: list[list[object]] = []
    for raw_row in existing_rows:
        if not raw_row or not str(raw_row[0]).strip():
            continue
        padded = list(raw_row[: len(HISTORY_HEADERS)]) + [""] * max(
            0, len(HISTORY_HEADERS) - len(raw_row)
        )
        raw_ts = str(padded[0]).strip()
        parsed_ts = pd.to_datetime(raw_ts, errors="coerce")
        formatted_ts = parsed_ts.strftime("%Y-%m-%d %H:%M") if pd.notna(parsed_ts) else raw_ts
        cleaned: list[object] = [formatted_ts] + [
            _coerce_history_cell(cell) for cell in padded[1:]
        ]
        if cleaned[6] == "" and all(isinstance(cleaned[idx], int) for idx in (2, 3, 4)):
            single_count = int(cleaned[2]) - int(cleaned[3]) - int(cleaned[4])
            if single_count >= 0:
                cleaned[2] = int(cleaned[3]) + int(cleaned[4])
                cleaned[6] = single_count
        normalized_existing.append(cleaned)

    # Put new_row first so Python's stable sort keeps it at the top on timestamp ties.
    combined = [list(new_row)] + normalized_existing
    combined.sort(key=_history_sort_key, reverse=True)
    return combined[:max_rows]


def _shrink_trend_frame(
    comparison: pd.DataFrame,
    *,
    fetched_at: str,
    raw: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """One current highest price per explicitly shrink-wrapped box.

    When raw records are available, compute peaks directly from explicit
    shrink_wrapped sealed_box rows so an unspecified listing from another store
    never suppresses a box's shrink-wrapped trend history.
    """
    day = datetime.fromisoformat(fetched_at).astimezone(JAPAN_TIME_ZONE).date().isoformat()
    required_raw_cols = {
        "product_kind",
        "condition",
        "price_yen",
        "product_name_normalized",
        "source",
    }
    if raw is not None and not raw.empty and required_raw_cols.issubset(raw.columns):
        mask = (
            (raw["product_kind"] == "sealed_box")
            & (raw["condition"] == "shrink_wrapped")
            & raw["price_yen"].notna()
        )
        if "stock_status" in raw.columns:
            mask = mask & (raw["stock_status"] == "active")
        explicit = raw[mask].copy()
        if explicit.empty:
            return pd.DataFrame(columns=TREND_HEADERS)
        explicit["normalized_name"] = (
            explicit["product_name_normalized"].astype(str).map(normalize_product_name)
        )
        explicit["price_int"] = pd.to_numeric(explicit["price_yen"], errors="coerce")
        explicit = explicit[(explicit["normalized_name"] != "") & explicit["price_int"].notna()]
        if explicit.empty:
            return pd.DataFrame(columns=TREND_HEADERS)
        explicit["price_int"] = explicit["price_int"].astype(int)
        per_store = (
            explicit.groupby(["normalized_name", "source"], as_index=False)["price_int"].max()
        )
        rows: list[dict[str, object]] = []
        for product_name, group in per_store.groupby("normalized_name", sort=True):
            best_price = int(group["price_int"].max())
            winners_raw = set(group.loc[group["price_int"] == best_price, "source"].astype(str))
            ordered_winners = [src for src in SOURCE_ORDER if src in winners_raw] + sorted(
                winners_raw - set(SOURCE_ORDER)
            )
            rows.append(
                {
                    "日付": day,
                    "商品名": str(product_name),
                    "最高値": best_price,
                    "最高値の店": _store_label(",".join(ordered_winners)),
                }
            )
        return pd.DataFrame(rows, columns=TREND_HEADERS)

    if comparison.empty:
        return pd.DataFrame(columns=TREND_HEADERS)
    eligible = comparison[
        (comparison["condition"] == "shrink_wrapped")
        & (~comparison["condition_inferred"].fillna(False).astype(bool))
        & comparison["best_price_yen"].notna()
    ].copy()
    if eligible.empty:
        return pd.DataFrame(columns=TREND_HEADERS)
    prepared = pd.DataFrame(
        {
            "日付": day,
            "商品名": eligible["product_name_normalized"].astype(str).map(normalize_product_name),
            "最高値": eligible["best_price_yen"].astype(int),
            "最高値の店": eligible["best_site"].map(_store_label),
        }
    )
    return prepared.sort_values(["商品名", "日付"], kind="mergesort").reset_index(drop=True)


def _trend_history_frame(
    rows: list[list[object]], *, sheet_title: str = TREND_SHEET_TITLE
) -> pd.DataFrame:
    """Read a narrow 4-column daily trend history table safely."""
    if not rows:
        return pd.DataFrame(columns=TREND_HEADERS)
    if rows[0][: len(TREND_HEADERS)] != TREND_HEADERS:
        raise ValueError(
            f"{sheet_title} の履歴ヘッダーが一致しないため、既存データを保護して更新を中止しました。"
        )
    values = [
        row[: len(TREND_HEADERS)]
        for row in rows[1:]
        if any(str(value).strip() for value in row[: len(TREND_HEADERS)])
    ]
    return pd.DataFrame(values, columns=TREND_HEADERS)


def _merge_trend_history(existing: pd.DataFrame, current: pd.DataFrame) -> pd.DataFrame:
    """Keep only the highest observed price for each normalized box on each JST date."""
    # Place current before existing so stable mergesort keeps current store labels on ties.
    combined = pd.concat([current, existing], ignore_index=True)
    if combined.empty:
        return pd.DataFrame(columns=TREND_HEADERS)
    combined = combined.copy()
    combined["日付"] = combined["日付"].astype(str).str.strip()
    combined["商品名"] = combined["商品名"].astype(str).map(normalize_product_name)
    # Existing Sheet values may be returned as formatted currency strings such
    # as "¥14,500". Keep them as history instead of treating them as invalid.
    combined["最高値"] = pd.to_numeric(
        combined["最高値"].astype(str).str.replace(r"[^0-9.-]", "", regex=True),
        errors="coerce",
    )
    combined = combined[
        (combined["日付"] != "") & (combined["商品名"] != "") & combined["最高値"].notna()
    ]
    combined["最高値"] = combined["最高値"].astype(int)
    combined = combined.sort_values(
        ["日付", "商品名", "最高値"], ascending=[True, True, False], kind="mergesort"
    )
    merged = combined.drop_duplicates(["日付", "商品名"], keep="first")
    return merged.sort_values(["商品名", "日付"], kind="mergesort").reset_index(drop=True)[
        TREND_HEADERS
    ]


def _format_date_headers(iso_dates: list[str]) -> list[str]:
    short_labels = [
        f"{day[5:7]}/{day[8:10]}" if len(day) >= 10 else day for day in iso_dates
    ]
    if len(set(short_labels)) == len(short_labels):
        return short_labels
    return [day.replace("-", "/") for day in iso_dates]


def _trend_sparkline_formula(row_number: int, num_dates: int) -> str:
    """Plot newest-first date columns chronologically (left = oldest, right = newest)."""
    if num_dates < 2:
        return ""
    start_col = _column_letter(len(TREND_FIXED_COLUMNS))
    end_col = _column_letter(len(TREND_FIXED_COLUMNS) + num_dates - 1)
    row_range = f"{start_col}{row_number}:{end_col}{row_number}"
    transposed = f"TRANSPOSE({row_range})"
    return (
        f"=IFERROR(SPARKLINE("
        f"SORT(FILTER({transposed},ISNUMBER({transposed})),"
        f"FILTER(SEQUENCE({num_dates}),ISNUMBER({transposed})),FALSE),"
        f'{{"charttype","line";"color","#15735a";"linewidth",2}}),"")'
    )


def _trend_matrix_frame(
    trend_history: pd.DataFrame,
    *,
    max_dates: int = TREND_WINDOW_DATES,
    recency_days: int = TREND_ACTIVE_RECENCY_DAYS,
) -> pd.DataFrame:
    """Build a compact 1-row-per-box matrix over the latest N dates (newest-first)."""
    if trend_history.empty:
        return pd.DataFrame(columns=TREND_FIXED_COLUMNS)

    all_dates_desc = sorted(trend_history["日付"].astype(str).unique(), reverse=True)
    window_dates = all_dates_desc[:max_dates]
    date_headers = _format_date_headers(window_dates)
    date_to_header = dict(zip(window_dates, date_headers))
    columns = TREND_FIXED_COLUMNS + date_headers

    latest_global_iso = all_dates_desc[0]
    try:
        latest_global_day = date.fromisoformat(latest_global_iso)
        cutoff_iso = (latest_global_day - timedelta(days=recency_days)).isoformat()
    except ValueError:
        cutoff_iso = ""

    sortable_rows: list[tuple[tuple[object, ...], dict[str, object]]] = []
    for product_name, group in trend_history.groupby("商品名", sort=True):
        ordered = group.sort_values("日付", kind="mergesort")
        records = list(
            zip(
                ordered["日付"].astype(str),
                ordered["最高値"].astype(int),
                ordered["最高値の店"].astype(str),
            )
        )
        latest_day, latest_price, latest_store = records[-1]
        if cutoff_iso and latest_day < cutoff_iso:
            continue

        is_current = latest_day == latest_global_iso
        prev_diff: int | str = (
            records[-1][1] - records[-2][1] if is_current and len(records) >= 2 else ""
        )

        diff_7d: int | str = ""
        if is_current:
            try:
                target_7d = (date.fromisoformat(latest_day) - timedelta(days=7)).isoformat()
                older_or_equal = [price for obs_day, price, _ in records if obs_day <= target_7d]
                if older_or_equal:
                    diff_7d = latest_price - older_or_equal[-1]
            except ValueError:
                diff_7d = ""

        row: dict[str, object] = {
            "商品名": str(product_name),
            "最新最高値": latest_price,
            "最高値の店": latest_store,
            "前回比": prev_diff,
            "7日前比": diff_7d,
            "30日推移": "",
        }
        for header in date_headers:
            row[header] = ""
        for obs_day, price, _ in records:
            if obs_day in date_to_header:
                row[date_to_header[obs_day]] = price

        abs_prev = abs(prev_diff) if isinstance(prev_diff, int) else 0
        abs_7d = abs(diff_7d) if isinstance(diff_7d, int) else 0
        sort_key = (
            -(1 if is_current else 0),
            -(1 if abs_prev > 0 else 0),
            -abs_prev,
            -(1 if abs_7d > 0 else 0),
            -abs_7d,
            -latest_price,
            str(product_name),
        )
        sortable_rows.append((sort_key, row))

    sortable_rows.sort(key=lambda item: item[0])
    if not sortable_rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame([row for _, row in sortable_rows], columns=columns)


def _previous_shrink_prices(
    trend_history: pd.DataFrame,
    comparison: pd.DataFrame,
    *,
    current_day: str,
) -> dict[str, int]:
    """Return prior explicit shrink-wrapped peak for boxes whose comparison peak matches today's."""
    if trend_history.empty or comparison.empty:
        return {}
    today_rows = trend_history[trend_history["日付"] == current_day]
    today_peaks = dict(zip(today_rows["商品名"].astype(str), today_rows["最高値"].astype(int)))

    prior = trend_history[trend_history["日付"] < current_day].sort_values(
        ["商品名", "日付"], kind="mergesort"
    )
    if prior.empty:
        return {}
    latest_prior = prior.drop_duplicates(["商品名"], keep="last")
    prior_map = dict(zip(latest_prior["商品名"].astype(str), latest_prior["最高値"].astype(int)))

    eligible_comp = comparison[
        (comparison["condition"] == "shrink_wrapped") & comparison["best_price_yen"].notna()
    ]
    result: dict[str, int] = {}
    for _, record in eligible_comp.iterrows():
        name = str(record["product_name_normalized"])
        comp_best = _optional_int(record["best_price_yen"])
        if (
            isinstance(comp_best, int)
            and name in prior_map
            and today_peaks.get(name) == comp_best
        ):
            result[name] = prior_map[name]
    return result


def _trend_chart_ids(spreadsheet: object, sheet_id: int) -> list[int]:
    metadata = spreadsheet.fetch_sheet_metadata(
        params={"fields": "sheets(properties(sheetId),charts(chartId))"}
    )
    for sheet in metadata.get("sheets", []):
        if sheet.get("properties", {}).get("sheetId") == sheet_id:
            return [int(chart["chartId"]) for chart in sheet.get("charts", [])]
    return []


def _trend_matrix_format_requests(
    sheet_id: int,
    frame: pd.DataFrame,
    chart_ids: list[int],
) -> list[dict[str, object]]:
    column_count = max(len(frame.columns), len(TREND_FIXED_COLUMNS))
    row_count = len(frame)
    num_date_cols = max(0, column_count - len(TREND_FIXED_COLUMNS))
    widths = TREND_FIXED_COLUMN_WIDTHS + [TREND_DATE_COLUMN_WIDTH] * num_date_cols

    requests: list[dict[str, object]] = [
        {"deleteEmbeddedObject": {"objectId": chart_id}} for chart_id in chart_ids
    ]
    requests += [
        _reset_format_request(sheet_id),
        _header_format_request(sheet_id, column_count),
        _freeze_request(sheet_id, rows=1, columns=2),
    ]
    requests += _row_height_requests(sheet_id, row_count)
    requests += [
        _note_request(sheet_id, 0, column, note)
        for column, note in TREND_HEADER_NOTES.items()
    ]
    requests += _column_width_requests(sheet_id, widths)
    if row_count:
        requests.append(_clip_request(sheet_id, row_count, column_count))
        requests += _zebra_requests(sheet_id, row_count, column_count)
        requests.append(_alignment_request(sheet_id, row_count, 1, 2, "RIGHT"))
        requests.append(_alignment_request(sheet_id, row_count, 3, 5, "RIGHT"))
        if num_date_cols > 0:
            requests.append(
                _alignment_request(
                    sheet_id, row_count, len(TREND_FIXED_COLUMNS), column_count, "RIGHT"
                )
            )
            requests.append(
                _number_format_request(
                    sheet_id,
                    row_count,
                    len(TREND_FIXED_COLUMNS),
                    column_count,
                    "NUMBER",
                    YEN_PATTERN,
                )
            )
        requests.append(_number_format_request(sheet_id, row_count, 1, 2, "NUMBER", YEN_PATTERN))
        requests.append(
            _number_format_request(sheet_id, row_count, 3, 5, "NUMBER", SIGNED_YEN_PATTERN)
        )
        requests += _delta_text_color_requests(sheet_id, list(frame["前回比"]), 3)
        requests += _delta_text_color_requests(sheet_id, list(frame["7日前比"]), 4)
    requests += _basic_filter_requests(sheet_id, row_count, column_count)
    return requests


def _publish_shrink_trends_with_history(
    spreadsheet: object,
    comparison: pd.DataFrame,
    *,
    fetched_at: str,
    raw: pd.DataFrame | None = None,
) -> tuple[dict[str, int], pd.DataFrame]:
    """Archive full daily shrink-wrapped history in a hidden tab and render a 30-day matrix."""
    import gspread
    from gspread.utils import ValueRenderOption

    archive_ws = None
    archive_existing = pd.DataFrame(columns=TREND_HEADERS)
    prev_archive_rows = 0
    try:
        archive_ws = spreadsheet.worksheet(TREND_ARCHIVE_SHEET_TITLE)
        raw_archive_rows = archive_ws.get_values(
            "A1:D", value_render_option=ValueRenderOption.unformatted
        )
        prev_archive_rows = max(0, len(raw_archive_rows) - 1)
        archive_existing = _trend_history_frame(
            raw_archive_rows, sheet_title=TREND_ARCHIVE_SHEET_TITLE
        )
    except gspread.WorksheetNotFound:
        archive_ws = None

    legacy_existing = pd.DataFrame(columns=TREND_HEADERS)
    try:
        trend_ws = spreadsheet.worksheet(TREND_SHEET_TITLE)
        chart_ids = _trend_chart_ids(spreadsheet, trend_ws.id)
        header_preview = trend_ws.get_values(
            "A1:F1", value_render_option=ValueRenderOption.unformatted
        )
        first_row = header_preview[0] if header_preview else []
        if first_row[: len(TREND_HEADERS)] == TREND_HEADERS:
            # First run after redesign: migrate all legacy vertical rows into the archive.
            legacy_rows = trend_ws.get_values(
                "A1:D", value_render_option=ValueRenderOption.unformatted
            )
            legacy_existing = _trend_history_frame(
                legacy_rows, sheet_title=TREND_SHEET_TITLE
            )
        elif (
            first_row
            and first_row[: len(TREND_FIXED_COLUMNS)] != TREND_FIXED_COLUMNS
            and archive_ws is None
        ):
            raise ValueError(
                f"{TREND_SHEET_TITLE} の履歴ヘッダーが一致しないため、既存データを保護して更新を中止しました。"
            )
    except gspread.WorksheetNotFound:
        trend_ws = spreadsheet.add_worksheet(title=TREND_SHEET_TITLE, rows=80, cols=36)
        chart_ids = []

    existing_combined = _merge_trend_history(archive_existing, legacy_existing)
    current_trend = _shrink_trend_frame(comparison, fetched_at=fetched_at, raw=raw)
    trend = _merge_trend_history(existing_combined, current_trend)

    archive_needed_rows = max(len(trend) + 20, 100)
    if archive_ws is None:
        archive_ws = spreadsheet.add_worksheet(
            title=TREND_ARCHIVE_SHEET_TITLE,
            rows=archive_needed_rows,
            cols=len(TREND_HEADERS),
        )
    elif archive_ws.row_count < archive_needed_rows or archive_ws.col_count < len(TREND_HEADERS):
        archive_ws.resize(
            rows=max(archive_ws.row_count, archive_needed_rows),
            cols=max(archive_ws.col_count, len(TREND_HEADERS)),
        )
    # Write merged history without clearing beforehand so a partial failure can never wipe history.
    archive_ws.update(values=_sheet_values(trend), range_name="A1", value_input_option="RAW")
    if prev_archive_rows > len(trend) and hasattr(archive_ws, "batch_clear"):
        archive_ws.batch_clear([f"A{len(trend) + 2}:D{prev_archive_rows + 1}"])

    matrix = _trend_matrix_frame(trend)
    num_dates = max(0, len(matrix.columns) - len(TREND_FIXED_COLUMNS))
    needed_rows = max(len(matrix) + 5, 20)
    needed_cols = max(len(matrix.columns), len(TREND_FIXED_COLUMNS) + 1)

    if chart_ids:
        spreadsheet.batch_update(
            {
                "requests": [
                    {"deleteEmbeddedObject": {"objectId": chart_id}}
                    for chart_id in chart_ids
                ]
            }
        )
    if hasattr(trend_ws, "clear"):
        trend_ws.clear()
    if trend_ws.row_count != needed_rows or trend_ws.col_count != needed_cols:
        trend_ws.resize(rows=needed_rows, cols=needed_cols)
    trend_ws.update(values=_sheet_values(matrix), range_name="A1", value_input_option="RAW")
    if not matrix.empty and num_dates >= 2:
        sparklines = [
            [_trend_sparkline_formula(row_idx, num_dates)]
            for row_idx in range(2, len(matrix) + 2)
        ]
        trend_ws.update(
            values=sparklines,
            range_name=f"F2:F{len(matrix) + 1}",
            value_input_option="USER_ENTERED",
        )

    requests = _trend_matrix_format_requests(trend_ws.id, matrix, [])
    requests.append(
        {
            "updateSheetProperties": {
                "properties": {"sheetId": archive_ws.id, "hidden": True},
                "fields": "hidden",
            }
        }
    )
    spreadsheet.batch_update({"requests": requests})

    current_day = datetime.fromisoformat(fetched_at).astimezone(JAPAN_TIME_ZONE).date().isoformat()
    return _previous_shrink_prices(trend, comparison, current_day=current_day), trend


def _publish_shrink_trends(
    spreadsheet: object,
    comparison: pd.DataFrame,
    *,
    fetched_at: str,
    raw: pd.DataFrame | None = None,
) -> dict[str, int]:
    """Backwards-compatible wrapper returning only previous shrink-wrapped prices."""
    previous_prices, _ = _publish_shrink_trends_with_history(
        spreadsheet,
        comparison,
        fetched_at=fetched_at,
        raw=raw,
    )
    return previous_prices


def _prompt_format_requests(sheet_id: int, row_count: int) -> list[dict[str, object]]:
    """Format the 発信プロンプト tab for single-cell copy/paste on PC and mobile."""
    column_count = len(PROMPT_SHEET_HEADERS)
    requests: list[dict[str, object]] = [
        _reset_format_request(sheet_id),
        _header_format_request(sheet_id, column_count),
        _freeze_request(sheet_id, rows=1, columns=2),
    ]
    requests += _row_height_requests(sheet_id, row_count, header_px=34, data_px=165)
    requests += [
        _note_request(sheet_id, 0, column, note)
        for column, note in PROMPT_HEADER_NOTES.items()
    ]
    requests += _column_width_requests(sheet_id, PROMPT_COLUMN_WIDTHS)
    if row_count:
        requests.append(
            {
                "repeatCell": {
                    "range": _grid_range(sheet_id, 1, row_count + 1, 0, column_count),
                    "cell": {
                        "userEnteredFormat": {
                            "wrapStrategy": "WRAP",
                            "verticalAlignment": "TOP",
                        }
                    },
                    "fields": "userEnteredFormat(wrapStrategy,verticalAlignment)",
                }
            }
        )
        requests += _zebra_requests(sheet_id, row_count, column_count)
        requests.append(
            {
                "repeatCell": {
                    "range": _grid_range(sheet_id, 1, row_count + 1, 0, 1),
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": _color(PROMPT_CATEGORY_ACCENT_HEX),
                            "textFormat": {"bold": True, "foregroundColor": _color(HEADER_BACKGROUND_HEX)},
                            "horizontalAlignment": "CENTER",
                            "verticalAlignment": "TOP",
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)",
                }
            }
        )
        requests.append(
            {
                "repeatCell": {
                    "range": _grid_range(sheet_id, 1, row_count + 1, 1, 2),
                    "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                    "fields": "userEnteredFormat.textFormat",
                }
            }
        )
    return requests


def _publish_prompt_sheet(spreadsheet: object, bundle: PromptBundle) -> object:
    """Write store-anonymized AI prompt entries into the dedicated 発信プロンプト tab."""
    rows = bundle.to_sheet_rows()
    data_row_count = max(0, len(rows) - 1)
    needed_rows = max(len(rows) + 3, 15)
    needed_columns = len(PROMPT_SHEET_HEADERS)
    try:
        worksheet = spreadsheet.worksheet(PROMPT_SHEET_TITLE)
        worksheet.clear()
        if worksheet.row_count != needed_rows or worksheet.col_count != needed_columns:
            worksheet.resize(rows=needed_rows, cols=needed_columns)
    except Exception as exc:
        if exc.__class__.__name__ != "WorksheetNotFound":
            raise
        worksheet = spreadsheet.add_worksheet(
            title=PROMPT_SHEET_TITLE,
            rows=needed_rows,
            cols=needed_columns,
        )
    # Use RAW so lines starting with '+', '-', or '=' in prompts are never parsed as formulas.
    worksheet.update(values=rows, range_name="A1", value_input_option="RAW")
    spreadsheet.batch_update({"requests": _prompt_format_requests(worksheet.id, data_row_count)})
    return worksheet


def _remove_deprecated_summary_sources(spreadsheet: object, summary: object) -> None:
    """Remove retired store rows (such as 買取マッチョ) from the hand-made source table."""
    if not (
        hasattr(summary, "get_values")
        and hasattr(summary, "id")
        and hasattr(spreadsheet, "batch_update")
    ):
        return
    rows = summary.get_values("A10:B16")
    delete_requests = [
        {
            "deleteDimension": {
                "range": {
                    "sheetId": summary.id,
                    "dimension": "ROWS",
                    "startIndex": 9 + offset,
                    "endIndex": 10 + offset,
                }
            }
        }
        for offset, row in reversed(list(enumerate(rows)))
        if row and str(row[0]).strip() in REMOVED_SUMMARY_SOURCES
    ]
    if delete_requests:
        spreadsheet.batch_update({"requests": delete_requests})


def _ensure_summary_sheet(spreadsheet: object) -> object:
    try:
        summary = spreadsheet.worksheet(SUMMARY_SHEET_TITLE)
    except Exception as exc:
        # Avoid importing gspread exception classes in this helper.
        if exc.__class__.__name__ != "WorksheetNotFound":
            raise
        summary = spreadsheet.add_worksheet(title=SUMMARY_SHEET_TITLE, rows=30, cols=9)
    summary.update_acell("A1", SPREADSHEET_TITLE)
    # Counters are refreshed every run so the labels keep matching the tabs.
    # Nothing outside A3:B8 is written directly: row 9 is the merged link and
    # the rows under it hold the source table.
    summary.update(
        values=SUMMARY_COUNTER_ROWS,
        range_name=SUMMARY_COUNTER_RANGE,
        value_input_option="USER_ENTERED",
    )
    # Keep the smartphone update entry point even after future cloud refreshes.
    # Only the top-left cell is written because A9:B9 is merged in the live sheet.
    summary.update(
        values=[[MANUAL_UPDATE_FORMULA]],
        range_name="A9",
        value_input_option="USER_ENTERED",
    )
    _remove_deprecated_summary_sources(spreadsheet, summary)
    return summary


def _reorder_sheets(spreadsheet: object) -> None:
    desired_order = [
        (SUMMARY_SHEET_TITLE, False),
        (COMPARISON_SHEET_TITLE, False),
        (NO_SHRINK_SHEET_TITLE, False),
        (TREND_SHEET_TITLE, False),
        (SINGLE_LISTING_SHEET_TITLE, False),
        (STORE_GUIDE_SHEET_TITLE, False),
        (HISTORY_SHEET_TITLE, False),
        (RAW_SHEET_TITLE, False),
        (PROMPT_SHEET_TITLE, False),
        (TREND_ARCHIVE_SHEET_TITLE, True),
    ]
    requests: list[dict[str, object]] = []
    for target_index, (title, hidden) in enumerate(desired_order):
        try:
            ws = spreadsheet.worksheet(title)
        except Exception:
            continue
        requests.append(
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": ws.id,
                        "index": target_index,
                        "hidden": hidden,
                    },
                    "fields": "index,hidden",
                }
            }
        )
    if requests:
        spreadsheet.batch_update({"requests": requests})


def publish_frames(
    *,
    spreadsheet_id: str,
    credentials_file: str | Path,
    comparison: pd.DataFrame,
    raw: pd.DataFrame,
    fetched_at: str | None = None,
    error_count: int = 0,
    prompt_output_dir: str | Path | None = None,
    skip_prompts: bool = False,
    tool_base_url: str = TOOL_SITE_BASE_URL,
    web_market_json_path: str | Path | None = None,
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
    spreadsheet.update_title(SPREADSHEET_TITLE)

    effective_fetched_at = fetched_at
    if not effective_fetched_at and not raw.empty and "fetched_at" in raw:
        effective_fetched_at = str(raw["fetched_at"].dropna().iloc[0])
    if not effective_fetched_at:
        effective_fetched_at = datetime.now(JAPAN_TIME_ZONE).isoformat(timespec="seconds")

    previous_prices, trend_history = _publish_shrink_trends_with_history(
        spreadsheet,
        comparison,
        fetched_at=effective_fetched_at,
        raw=raw,
    )

    sheet_plans = (
        (
            COMPARISON_SHEET_TITLE,
            _comparison_sheet_frame(comparison, previous_prices=previous_prices),
            _comparison_format_requests,
        ),
        (
            NO_SHRINK_SHEET_TITLE,
            _no_shrink_sheet_frame(comparison),
            _no_shrink_format_requests,
        ),
        (
            SINGLE_LISTING_SHEET_TITLE,
            _single_listing_sheet_frame(comparison),
            _single_listing_format_requests,
        ),
        (
            STORE_GUIDE_SHEET_TITLE,
            _store_guide_sheet_frame(raw),
            _store_guide_format_requests,
        ),
        (RAW_SHEET_TITLE, _raw_sheet_frame(raw), _raw_format_requests),
    )
    format_requests: list[dict[str, object]] = []
    for title, frame, build_requests in sheet_plans:
        needed_rows = max(len(frame) + 5, 20)
        needed_columns = max(len(frame.columns), 4)
        try:
            worksheet = spreadsheet.worksheet(title)
            worksheet.clear()
            if worksheet.row_count != needed_rows or worksheet.col_count != needed_columns:
                worksheet.resize(rows=needed_rows, cols=needed_columns)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(
                title=title,
                rows=needed_rows,
                cols=needed_columns,
            )
        values = _sheet_values(frame)
        worksheet.update(values=values, range_name="A1", value_input_option="RAW")
        format_requests += build_requests(worksheet.id, frame)
    if format_requests:
        spreadsheet.batch_update({"requests": format_requests})

    try:
        history = spreadsheet.worksheet(HISTORY_SHEET_TITLE)
        existing_history = history.get_values("A2:G")
    except gspread.WorksheetNotFound:
        history = spreadsheet.add_worksheet(
            title=HISTORY_SHEET_TITLE, rows=50, cols=len(HISTORY_HEADERS)
        )
        existing_history = []

    new_history_row = _history_row(
        comparison,
        raw,
        fetched_at=effective_fetched_at,
        error_count=error_count,
    )
    prepared_history = _prepare_history_rows(existing_history, new_history_row)
    history_needed_rows = max(len(prepared_history) + 5, 20)
    history.clear()
    if history.row_count != history_needed_rows or history.col_count != len(HISTORY_HEADERS):
        history.resize(rows=history_needed_rows, cols=len(HISTORY_HEADERS))
    history.update(
        values=[HISTORY_HEADERS] + prepared_history,
        range_name="A1",
        value_input_option="USER_ENTERED",
    )
    spreadsheet.batch_update(
        {"requests": _history_format_requests(history.id, prepared_history)}
    )

    _ensure_summary_sheet(spreadsheet)

    insights = None
    if not skip_prompts or web_market_json_path is not None:
        insights = analyze_market(
            comparison,
            trend_history,
            fetched_at=effective_fetched_at,
        )
    if not skip_prompts and insights is not None:
        bundle = build_prompt_bundle(insights, tool_base_url=tool_base_url)
        _publish_prompt_sheet(spreadsheet, bundle)
        if prompt_output_dir is not None:
            write_prompt_outputs(insights, bundle, prompt_output_dir)

    if web_market_json_path is not None:
        active_store_count = (
            int(raw["source"].dropna().nunique())
            if raw is not None and not raw.empty and "source" in raw.columns
            else None
        )
        write_web_market_json(
            web_market_json_path,
            comparison,
            trend_history,
            fetched_at=effective_fetched_at,
            active_store_count=active_store_count,
            insights=insights,
        )

    _reorder_sheets(spreadsheet)
    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
