from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .config import AppConfig
from .models import AlertRow, ComparisonRow, PriceItem


LOGGER = logging.getLogger(__name__)
JAPAN_TIME_ZONE = timezone(timedelta(hours=9), name="JST")

SUMMARY_SHEET = "サマリー"
COMPARISON_SHEET = "比較"
TREND_SHEET = "価格推移"
ALERTS_SHEET = "目標アラート"
SINGLE_SHEET = "単独掲載"
HISTORY_SHEET = "更新履歴"
RAW_SHEET = "全取得"
ARCHIVE_SHEET = "推移データ（保管用）"

ARCHIVE_HEADERS = ["日付", "商品名", "状態", "ベスト価格", "ベスト店舗"]
TREND_FIXED_COLUMNS = ["商品名", "状態", "最新価格", "ベスト店舗", "前回比", "7日前比", "30日推移"]
TREND_WINDOW_DATES = 30
MAX_HISTORY_ROWS = 365

HISTORY_HEADERS = [
    "実行日時",
    "全取得件数",
    "比較対象（2サイト以上）",
    "目標達成件数",
    "単独掲載",
    "取得エラー",
]

HEADER_BG = {"red": 0.122, "green": 0.220, "blue": 0.392}  # #1F3864
WHITE = {"red": 1.0, "green": 1.0, "blue": 1.0}
ZEBRA_BG = {"red": 0.969, "green": 0.976, "blue": 0.988}  # #F7F9FC
BEST_BG = {"red": 0.776, "green": 0.937, "blue": 0.808}  # #C6EFCE
ALERT_HIT_BG = {"red": 0.996, "green": 0.949, "blue": 0.800}  # #FFF2CC
RED_TEXT = {"red": 0.753, "green": 0.0, "blue": 0.0}  # #C00000
GOLD_TEXT = {"red": 0.749, "green": 0.561, "blue": 0.0}  # #BF8F00
GOOD_DELTA_TEXT = {"red": 0.075, "green": 0.451, "blue": 0.200}  # #137333
BAD_DELTA_TEXT = {"red": 0.098, "green": 0.404, "blue": 0.824}  # #1967D2
FLAT_TEXT = {"red": 0.502, "green": 0.525, "blue": 0.545}  # #80868B


def _col_letter(zero_based_index: int) -> str:
    value = zero_based_index + 1
    letters: list[str] = []
    while value > 0:
        value, rem = divmod(value - 1, 26)
        letters.append(chr(ord("A") + rem))
    return "".join(reversed(letters))


def _currency_pattern(symbol: str) -> str:
    safe = symbol or "¥"
    return f"{safe}#,##0"


def _signed_currency_pattern(symbol: str) -> str:
    safe = symbol or "¥"
    return f'+{safe}#,##0;-{safe}#,##0;"±0"'


def _sparkline_formula(row_number: int, num_dates: int) -> str:
    """新しい順の日付列を左(古)→右(新)の時系列ミニグラフとして描画する数式。"""
    if num_dates < 2:
        return ""
    start_col = _col_letter(len(TREND_FIXED_COLUMNS))
    end_col = _col_letter(len(TREND_FIXED_COLUMNS) + num_dates - 1)
    row_range = f"{start_col}{row_number}:{end_col}{row_number}"
    transposed = f"TRANSPOSE({row_range})"
    return (
        f"=IFERROR(SPARKLINE("
        f"SORT(FILTER({transposed},ISNUMBER({transposed})),"
        f"FILTER(SEQUENCE({num_dates}),ISNUMBER({transposed})),FALSE),"
        f'{{"charttype","line";"color","#15735a";"linewidth",2}}),"")'
    )


def _merge_archive_records(
    existing_rows: list[list[Any]],
    all_rows: list[ComparisonRow],
    *,
    current_day: str,
) -> list[dict[str, Any]]:
    """既存の日次アーカイブと今回の結果を (日付, 商品名, 状態) で統合する。"""
    merged: dict[tuple[str, str, str], dict[str, Any]] = {}

    for raw_row in existing_rows:
        if len(raw_row) < 4:
            continue
        day = str(raw_row[0]).strip()
        name = str(raw_row[1]).strip()
        condition = str(raw_row[2]).strip() or "標準"
        try:
            price = int(float(str(raw_row[3]).replace(",", "").replace("¥", "").strip()))
        except ValueError:
            continue
        store = str(raw_row[4]).strip() if len(raw_row) >= 5 else ""
        if day and name and price > 0:
            merged[(day, name, condition)] = {
                "date": day,
                "name": name,
                "condition": condition,
                "price": price,
                "store": store,
            }

    for row in all_rows:
        merged[(current_day, row.name_normalized, row.condition)] = {
            "date": current_day,
            "name": row.name_normalized,
            "condition": row.condition,
            "price": row.best_price_yen,
            "store": row.best_source_label,
        }

    records = list(merged.values())
    records.sort(key=lambda r: (r["date"], r["name"], r["condition"]))
    return records


def _previous_price_lookup(
    archive_records: list[dict[str, Any]],
    *,
    current_day: str,
) -> dict[tuple[str, str], int]:
    """前日以前でもっとも新しい日のベスト価格を (商品名, 状態) ごとに返す。"""
    latest_before_today: dict[tuple[str, str], tuple[str, int]] = {}
    for rec in archive_records:
        if rec["date"] >= current_day:
            continue
        key = (rec["name"], rec["condition"])
        prev = latest_before_today.get(key)
        if prev is None or rec["date"] > prev[0]:
            latest_before_today[key] = (rec["date"], rec["price"])
    return {key: price for key, (_, price) in latest_before_today.items()}


def _build_trend_matrix(
    archive_records: list[dict[str, Any]],
    *,
    max_dates: int = TREND_WINDOW_DATES,
) -> tuple[list[str], list[list[Any]], int]:
    """1商品1行の横型マトリクス（新しい日付が左）を構築する。"""
    if not archive_records:
        return list(TREND_FIXED_COLUMNS), [], 0

    all_dates = sorted({rec["date"] for rec in archive_records}, reverse=True)
    window_dates = all_dates[:max_dates]
    date_headers = [d[5:].replace("-", "/") if len(d) >= 10 else d for d in window_dates]

    by_item: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for rec in archive_records:
        by_item.setdefault((rec["name"], rec["condition"]), []).append(rec)

    matrix_entries: list[tuple[int, int, str, list[Any]]] = []
    for (name, condition), entries in by_item.items():
        entries.sort(key=lambda r: r["date"])
        latest = entries[-1]
        latest_price = latest["price"]
        latest_store = latest["store"]

        prev_delta: int | str = ""
        if len(entries) >= 2:
            prev_delta = latest_price - entries[-2]["price"]

        delta_7d: int | str = ""
        try:
            latest_dt = date.fromisoformat(latest["date"])
            cutoff_7d = (latest_dt - timedelta(days=7)).isoformat()
            older = [e for e in entries if e["date"] <= cutoff_7d]
            if older:
                delta_7d = latest_price - older[-1]["price"]
        except ValueError:
            pass

        price_by_day = {e["date"]: e["price"] for e in entries}
        day_cells = [price_by_day.get(day, "") for day in window_dates]

        row_values: list[Any] = [
            name,
            condition,
            latest_price,
            latest_store,
            prev_delta,
            delta_7d,
            "",  # SPARKLINE placeholder
            *day_cells,
        ]
        moved_flag = 0 if (isinstance(prev_delta, int) and prev_delta != 0) else 1
        abs_move = abs(prev_delta) if isinstance(prev_delta, int) else 0
        matrix_entries.append((moved_flag, -abs_move, name, row_values))

    matrix_entries.sort(key=lambda entry: (entry[0], entry[1], entry[2]))
    headers = list(TREND_FIXED_COLUMNS) + date_headers
    rows = [entry[3] for entry in matrix_entries]
    return headers, rows, len(window_dates)


def _get_or_create_worksheet(spreadsheet: Any, title: str, rows: int, cols: int) -> Any:
    try:
        ws = spreadsheet.worksheet(title)
    except Exception as exc:
        if exc.__class__.__name__ != "WorksheetNotFound":
            raise
        return spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)

    if hasattr(ws, "clear"):
        ws.clear()
    if getattr(ws, "row_count", rows) != rows or getattr(ws, "col_count", cols) != cols:
        ws.resize(rows=rows, cols=cols)
    return ws


def _basic_table_format_requests(
    sheet_id: int,
    *,
    num_rows: int,
    num_cols: int,
    col_widths: list[int],
    currency_cols: list[int] | None = None,
    signed_currency_cols: list[int] | None = None,
    percent_cols: list[int] | None = None,
    currency_symbol: str = "¥",
) -> list[dict[str, Any]]:
    """ヘッダー装飾・先頭行固定・ゼブラ配色・列幅・数値書式を1回の batch_update にまとめる。"""
    requests: list[dict[str, Any]] = [
        # 全体書式リセット
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id},
                "cell": {"userEnteredFormat": {}},
                "fields": "userEnteredFormat",
            }
        },
        # 先頭行固定
        {
            "updateSheetProperties": {
                "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
                "fields": "gridProperties.frozenRowCount",
            }
        },
        # ヘッダー行（濃紺＋白太字）
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": num_cols,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": HEADER_BG,
                        "textFormat": {"foregroundColor": WHITE, "bold": True},
                        "verticalAlignment": "MIDDLE",
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment)",
            }
        },
    ]

    # ゼブラ配色
    for row_idx in range(1, num_rows):
        if row_idx % 2 == 0:
            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": row_idx,
                            "endRowIndex": row_idx + 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": num_cols,
                        },
                        "cell": {"userEnteredFormat": {"backgroundColor": ZEBRA_BG}},
                        "fields": "userEnteredFormat.backgroundColor",
                    }
                }
            )

    # 列幅
    for col_idx, width in enumerate(col_widths[:num_cols]):
        requests.append(
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": col_idx,
                        "endIndex": col_idx + 1,
                    },
                    "properties": {"pixelSize": width},
                    "fields": "pixelSize",
                }
            }
        )

    if num_rows > 1:
        for col_idx in currency_cols or []:
            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "endRowIndex": num_rows,
                            "startColumnIndex": col_idx,
                            "endColumnIndex": col_idx + 1,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "numberFormat": {"type": "CURRENCY", "pattern": _currency_pattern(currency_symbol)}
                            }
                        },
                        "fields": "userEnteredFormat.numberFormat",
                    }
                }
            )
        for col_idx in signed_currency_cols or []:
            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "endRowIndex": num_rows,
                            "startColumnIndex": col_idx,
                            "endColumnIndex": col_idx + 1,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "numberFormat": {
                                    "type": "NUMBER",
                                    "pattern": _signed_currency_pattern(currency_symbol),
                                }
                            }
                        },
                        "fields": "userEnteredFormat.numberFormat",
                    }
                }
            )
        for col_idx in percent_cols or []:
            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "endRowIndex": num_rows,
                            "startColumnIndex": col_idx,
                            "endColumnIndex": col_idx + 1,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "numberFormat": {"type": "PERCENT", "pattern": "0.0%"}
                            }
                        },
                        "fields": "userEnteredFormat.numberFormat",
                    }
                }
            )
    return requests


def _latest_history_expr(col_letter: str) -> str:
    return (
        f"IFERROR(INDEX({HISTORY_SHEET}!{col_letter}:{col_letter},"
        f"MATCH(MAX({HISTORY_SHEET}!A2:A),{HISTORY_SHEET}!A:A,0)),0)"
    )


def _format_timestamp_for_sheet(fetched_at: str) -> str:
    try:
        dt = datetime.fromisoformat(fetched_at).astimezone(JAPAN_TIME_ZONE)
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return fetched_at


def publish_to_sheets(
    *,
    spreadsheet_id: str,
    credentials_file: str | Path,
    config: AppConfig,
    items: list[PriceItem],
    compared_rows: list[ComparisonRow],
    single_rows: list[ComparisonRow],
    alert_rows: list[AlertRow],
    fetched_at: str,
    error_count: int = 0,
    client_override: Any = None,
) -> str:
    """Googleスプレッドシートへ7タブ＋非表示アーカイブを整形出力する。"""
    if client_override is not None:
        client = client_override
    else:
        try:
            import gspread
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "Googleスプレッドシート連携には requirements-google.txt のインストールが必要です。\n"
                "実行コマンド: python -m pip install -r requirements-google.txt"
            ) from exc
        client = gspread.service_account(filename=str(credentials_file))

    spreadsheet = client.open_by_key(spreadsheet_id)
    if hasattr(spreadsheet, "update_title"):
        spreadsheet.update_title(config.project.title)

    mode = config.project.comparison_mode
    currency = config.project.currency_symbol
    best_label = "最安値" if mode == "lowest" else "最高値"
    best_store_label = "最安の店" if mode == "lowest" else "最高値の店"
    enabled_sources = config.enabled_sources

    try:
        current_day = datetime.fromisoformat(fetched_at).astimezone(JAPAN_TIME_ZONE).date().isoformat()
    except ValueError:
        current_day = datetime.now(JAPAN_TIME_ZONE).date().isoformat()

    # 1. 非表示アーカイブの読込・統合（履歴を絶対に消さないようクリアせず上書き）
    try:
        archive_ws = spreadsheet.worksheet(ARCHIVE_SHEET)
        existing_archive = archive_ws.get_values("A2:E")
    except Exception as exc:
        if exc.__class__.__name__ != "WorksheetNotFound":
            raise
        archive_ws = spreadsheet.add_worksheet(title=ARCHIVE_SHEET, rows=200, cols=len(ARCHIVE_HEADERS))
        existing_archive = []

    all_active_rows = compared_rows + single_rows
    archive_records = _merge_archive_records(existing_archive, all_active_rows, current_day=current_day)
    archive_needed_rows = max(len(archive_records) + 20, 100)
    if getattr(archive_ws, "row_count", 0) < archive_needed_rows or getattr(archive_ws, "col_count", 0) < len(ARCHIVE_HEADERS):
        archive_ws.resize(
            rows=max(getattr(archive_ws, "row_count", 0), archive_needed_rows),
            cols=max(getattr(archive_ws, "col_count", 0), len(ARCHIVE_HEADERS)),
        )
    archive_values = [ARCHIVE_HEADERS] + [
        [r["date"], r["name"], r["condition"], r["price"], r["store"]] for r in archive_records
    ]
    archive_ws.update(values=archive_values, range_name="A1", value_input_option="RAW")

    previous_prices = _previous_price_lookup(archive_records, current_day=current_day)

    all_format_requests: list[dict[str, Any]] = [
        {
            "updateSheetProperties": {
                "properties": {"sheetId": archive_ws.id, "hidden": True},
                "fields": "hidden",
            }
        }
    ]

    # 2. 価格推移シート（横型マトリクス＋SPARKLINE）
    trend_headers, trend_rows, num_dates = _build_trend_matrix(archive_records)
    trend_ws = _get_or_create_worksheet(
        spreadsheet,
        TREND_SHEET,
        rows=max(len(trend_rows) + 5, 20),
        cols=max(len(trend_headers), len(TREND_FIXED_COLUMNS) + 1),
    )
    trend_ws.update(values=[trend_headers] + trend_rows, range_name="A1", value_input_option="RAW")
    if trend_rows and num_dates >= 2:
        spark_col = _col_letter(len(TREND_FIXED_COLUMNS) - 1)
        sparklines = [[_sparkline_formula(r_idx, num_dates)] for r_idx in range(2, len(trend_rows) + 2)]
        trend_ws.update(
            values=sparklines,
            range_name=f"{spark_col}2:{spark_col}{len(trend_rows) + 1}",
            value_input_option="USER_ENTERED",
        )
    trend_widths = [240, 85, 95, 130, 90, 90, 130] + [78] * num_dates
    all_format_requests += _basic_table_format_requests(
        trend_ws.id,
        num_rows=len(trend_rows) + 1,
        num_cols=len(trend_headers),
        col_widths=trend_widths,
        currency_cols=[2] + list(range(len(TREND_FIXED_COLUMNS), len(trend_headers))),
        signed_currency_cols=[4, 5],
        currency_symbol=currency,
    )

    # 3. 比較シート（2サイト以上）
    comp_headers = [
        "商品名",
        "状態",
        best_label,
        "前回比",
        best_store_label,
        "差率",
        "差額",
        *[source.label for source in enabled_sources],
        "目標判定",
    ]
    comp_values: list[list[Any]] = [comp_headers]
    for row in compared_rows:
        prev = previous_prices.get((row.name_normalized, row.condition))
        delta: int | str = (row.best_price_yen - prev) if prev is not None else ""
        comp_values.append(
            [
                row.name_normalized,
                row.condition,
                row.best_price_yen,
                delta,
                row.best_source_label,
                "" if row.spread_rate is None else round(row.spread_rate, 4),
                "" if row.spread_yen is None else row.spread_yen,
                *[
                    "" if row.source_prices.get(source.id) is None else row.source_prices[source.id]
                    for source in enabled_sources
                ],
                "🎯 目標達成" if row.target_hit else ("監視中" if row.target_price_yen is not None else ""),
            ]
        )
    comp_ws = _get_or_create_worksheet(
        spreadsheet,
        COMPARISON_SHEET,
        rows=max(len(comp_values) + 5, 20),
        cols=max(len(comp_headers), 8),
    )
    comp_ws.update(values=comp_values, range_name="A1", value_input_option="RAW")

    source_col_start = 7
    source_col_indices = list(range(source_col_start, source_col_start + len(enabled_sources)))
    comp_widths = [250, 85, 95, 90, 130, 72, 90] + [100] * len(enabled_sources) + [105]
    all_format_requests += _basic_table_format_requests(
        comp_ws.id,
        num_rows=len(comp_values),
        num_cols=len(comp_headers),
        col_widths=comp_widths,
        currency_cols=[2, 6, *source_col_indices],
        signed_currency_cols=[3],
        percent_cols=[5],
        currency_symbol=currency,
    )

    # 比較シートのハイライト装飾（ベスト価格＝緑、高差率＝赤太字、高差額＝金太字、前回比色分け、目標達成＝黄）
    for row_idx, row in enumerate(compared_rows, start=1):
        # 各店舗セルでベスト価格に一致するセルを緑塗り
        for offset, source in enumerate(enabled_sources):
            price = row.source_prices.get(source.id)
            if price is not None and price == row.best_price_yen:
                col_i = source_col_start + offset
                all_format_requests.append(
                    {
                        "repeatCell": {
                            "range": {
                                "sheetId": comp_ws.id,
                                "startRowIndex": row_idx,
                                "endRowIndex": row_idx + 1,
                                "startColumnIndex": col_i,
                                "endColumnIndex": col_i + 1,
                            },
                            "cell": {"userEnteredFormat": {"backgroundColor": BEST_BG}},
                            "fields": "userEnteredFormat.backgroundColor",
                        }
                    }
                )
        # 差率しきい値
        if row.spread_rate is not None and row.spread_rate >= config.alerts.highlight_spread_rate:
            all_format_requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": comp_ws.id,
                            "startRowIndex": row_idx,
                            "endRowIndex": row_idx + 1,
                            "startColumnIndex": 5,
                            "endColumnIndex": 6,
                        },
                        "cell": {"userEnteredFormat": {"textFormat": {"foregroundColor": RED_TEXT, "bold": True}}},
                        "fields": "userEnteredFormat.textFormat",
                    }
                }
            )
        # 差額しきい値
        if row.spread_yen is not None and row.spread_yen >= config.alerts.highlight_spread_yen:
            all_format_requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": comp_ws.id,
                            "startRowIndex": row_idx,
                            "endRowIndex": row_idx + 1,
                            "startColumnIndex": 6,
                            "endColumnIndex": 7,
                        },
                        "cell": {"userEnteredFormat": {"textFormat": {"foregroundColor": GOLD_TEXT, "bold": True}}},
                        "fields": "userEnteredFormat.textFormat",
                    }
                }
            )
        # 目標達成バッジ
        if row.target_hit:
            target_col = len(comp_headers) - 1
            all_format_requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": comp_ws.id,
                            "startRowIndex": row_idx,
                            "endRowIndex": row_idx + 1,
                            "startColumnIndex": target_col,
                            "endColumnIndex": target_col + 1,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": ALERT_HIT_BG,
                                "textFormat": {"bold": True},
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat)",
                    }
                }
            )
        # 前回比の色分け（lowestなら値下がりがお得=緑、highestなら値上がりがお得=緑）
        delta_val = comp_values[row_idx][3]
        if isinstance(delta_val, int):
            if delta_val == 0:
                color = FLAT_TEXT
                bold = False
            else:
                is_favorable = (delta_val < 0) if mode == "lowest" else (delta_val > 0)
                color = GOOD_DELTA_TEXT if is_favorable else BAD_DELTA_TEXT
                bold = True
            all_format_requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": comp_ws.id,
                            "startRowIndex": row_idx,
                            "endRowIndex": row_idx + 1,
                            "startColumnIndex": 3,
                            "endColumnIndex": 4,
                        },
                        "cell": {"userEnteredFormat": {"textFormat": {"foregroundColor": color, "bold": bold}}},
                        "fields": "userEnteredFormat.textFormat",
                    }
                }
            )

    # 4. 目標アラートシート
    alert_headers = ["判定", "商品名", "状態", "目標価格", f"現在{best_label}", "目標との差", best_store_label, "商品URL"]
    alert_values: list[list[Any]] = [alert_headers]
    for row in alert_rows:
        alert_values.append(
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
        )
    alerts_ws = _get_or_create_worksheet(
        spreadsheet,
        ALERTS_SHEET,
        rows=max(len(alert_values) + 5, 20),
        cols=len(alert_headers),
    )
    alerts_ws.update(values=alert_values, range_name="A1", value_input_option="RAW")
    all_format_requests += _basic_table_format_requests(
        alerts_ws.id,
        num_rows=len(alert_values),
        num_cols=len(alert_headers),
        col_widths=[120, 240, 85, 100, 100, 95, 130, 240],
        currency_cols=[3, 4],
        signed_currency_cols=[5],
        currency_symbol=currency,
    )
    for row_idx, row in enumerate(alert_rows, start=1):
        if row.achieved:
            all_format_requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": alerts_ws.id,
                            "startRowIndex": row_idx,
                            "endRowIndex": row_idx + 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": len(alert_headers),
                        },
                        "cell": {"userEnteredFormat": {"backgroundColor": ALERT_HIT_BG}},
                        "fields": "userEnteredFormat.backgroundColor",
                    }
                }
            )

    # 5. 単独掲載シート
    single_headers = ["商品名", "状態", "掲載店", "価格", "商品URL"]
    single_values: list[list[Any]] = [single_headers]
    for row in single_rows:
        first_url = next((u for u in row.source_urls.values() if u), "")
        single_values.append([row.name_normalized, row.condition, row.best_source_label, row.best_price_yen, first_url])
    single_ws = _get_or_create_worksheet(
        spreadsheet,
        SINGLE_SHEET,
        rows=max(len(single_values) + 5, 20),
        cols=len(single_headers),
    )
    single_ws.update(values=single_values, range_name="A1", value_input_option="RAW")
    all_format_requests += _basic_table_format_requests(
        single_ws.id,
        num_rows=len(single_values),
        num_cols=len(single_headers),
        col_widths=[260, 85, 130, 100, 240],
        currency_cols=[3],
        currency_symbol=currency,
    )

    # 6. 全取得シート
    raw_headers = ["取得元", "商品名（原文）", "商品名（名寄せ後）", "状態", "価格", "在庫", "商品URL", "取得日時"]
    raw_values: list[list[Any]] = [raw_headers]
    for item in items:
        raw_values.append(
            [
                item.source_label,
                item.name_raw,
                item.name_normalized,
                item.condition,
                "" if item.price_yen is None else item.price_yen,
                "在庫あり" if item.stock_status == "available" else ("在庫切れ" if item.stock_status == "out_of_stock" else "不明"),
                item.url,
                _format_timestamp_for_sheet(item.fetched_at),
            ]
        )
    raw_ws = _get_or_create_worksheet(
        spreadsheet,
        RAW_SHEET,
        rows=max(len(raw_values) + 5, 20),
        cols=len(raw_headers),
    )
    raw_ws.update(values=raw_values, range_name="A1", value_input_option="RAW")
    all_format_requests += _basic_table_format_requests(
        raw_ws.id,
        num_rows=len(raw_values),
        num_cols=len(raw_headers),
        col_widths=[120, 260, 220, 85, 100, 85, 240, 140],
        currency_cols=[4],
        currency_symbol=currency,
    )

    # 7. 更新履歴シート（新しい順・最大365件）
    try:
        history_ws = spreadsheet.worksheet(HISTORY_SHEET)
        existing_history = history_ws.get_values("A2:F")
    except Exception as exc:
        if exc.__class__.__name__ != "WorksheetNotFound":
            raise
        history_ws = spreadsheet.add_worksheet(title=HISTORY_SHEET, rows=50, cols=len(HISTORY_HEADERS))
        existing_history = []

    hit_count = sum(1 for row in alert_rows if row.achieved)
    new_history_row = [
        _format_timestamp_for_sheet(fetched_at),
        len(items),
        len(compared_rows),
        hit_count,
        len(single_rows),
        error_count,
    ]
    cleaned_history = [new_history_row] + [
        row[: len(HISTORY_HEADERS)] for row in existing_history if row and any(str(c).strip() for c in row)
    ]
    cleaned_history = cleaned_history[:MAX_HISTORY_ROWS]

    history_rows_needed = max(len(cleaned_history) + 5, 20)
    if hasattr(history_ws, "clear"):
        history_ws.clear()
    if getattr(history_ws, "row_count", 0) != history_rows_needed or getattr(history_ws, "col_count", 0) != len(HISTORY_HEADERS):
        history_ws.resize(rows=history_rows_needed, cols=len(HISTORY_HEADERS))
    history_ws.update(
        values=[HISTORY_HEADERS] + cleaned_history,
        range_name="A1",
        value_input_option="USER_ENTERED",
    )
    all_format_requests += _basic_table_format_requests(
        history_ws.id,
        num_rows=len(cleaned_history) + 1,
        num_cols=len(HISTORY_HEADERS),
        col_widths=[150, 115, 165, 115, 105, 100],
        currency_symbol=currency,
    )

    # 8. サマリーシート
    summary_ws = _get_or_create_worksheet(spreadsheet, SUMMARY_SHEET, rows=30, cols=6)
    mode_desc = "最安値比較（安く買う）" if mode == "lowest" else "最高値比較（高く売る）"
    summary_rows: list[list[Any]] = [
        [config.project.title, f"モード: {mode_desc}"],
        [],
        ["最終更新", f'=IFERROR(MAX({HISTORY_SHEET}!A2:A),"")'],
        ["全取得件数", "=" + _latest_history_expr("B")],
        ["比較対象（2サイト以上）", "=" + _latest_history_expr("C")],
        ["🎯 目標価格達成件数", "=" + _latest_history_expr("D")],
        ["単独掲載（1サイトのみ）", "=" + _latest_history_expr("E")],
        ["取得エラー", "=" + _latest_history_expr("F")],
    ]
    if config.project.manual_update_url:
        summary_rows.append(
            [f'=HYPERLINK("{config.project.manual_update_url}","🔄 価格表を手動更新する")', "スマホから即時更新"]
        )
    else:
        summary_rows.append(["手動更新リンク", "config.json の manual_update_url を設定すると表示されます"])

    summary_rows.append([])
    summary_rows.append(["監視中の取得元サイト", "取得方式", "参照先"])
    for source in enabled_sources:
        ref_url = source.url or (source.urls[0] if source.urls else source.collector)
        summary_rows.append([source.label, source.type, ref_url])

    summary_ws.update(values=summary_rows, range_name="A1", value_input_option="USER_ENTERED")
    all_format_requests += [
        {
            "repeatCell": {
                "range": {"sheetId": summary_ws.id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 3},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": HEADER_BG,
                        "textFormat": {"foregroundColor": WHITE, "bold": True, "fontSize": 13},
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }
        },
        {
            "updateDimensionProperties": {
                "range": {"sheetId": summary_ws.id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1},
                "properties": {"pixelSize": 220},
                "fields": "pixelSize",
            }
        },
        {
            "updateDimensionProperties": {
                "range": {"sheetId": summary_ws.id, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 2},
                "properties": {"pixelSize": 180},
                "fields": "pixelSize",
            }
        },
        {
            "updateDimensionProperties": {
                "range": {"sheetId": summary_ws.id, "dimension": "COLUMNS", "startIndex": 2, "endIndex": 3},
                "properties": {"pixelSize": 320},
                "fields": "pixelSize",
            }
        },
    ]

    # タブの並び順を統一
    desired_order = [
        (SUMMARY_SHEET, False),
        (COMPARISON_SHEET, False),
        (TREND_SHEET, False),
        (ALERTS_SHEET, False),
        (SINGLE_SHEET, False),
        (HISTORY_SHEET, False),
        (RAW_SHEET, False),
        (ARCHIVE_SHEET, True),
    ]
    for target_idx, (title, hidden) in enumerate(desired_order):
        try:
            ws = spreadsheet.worksheet(title)
        except Exception:
            continue
        all_format_requests.append(
            {
                "updateSheetProperties": {
                    "properties": {"sheetId": ws.id, "index": target_idx, "hidden": hidden},
                    "fields": "index,hidden",
                }
            }
        )

    if all_format_requests and hasattr(spreadsheet, "batch_update"):
        spreadsheet.batch_update({"requests": all_format_requests})

    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
