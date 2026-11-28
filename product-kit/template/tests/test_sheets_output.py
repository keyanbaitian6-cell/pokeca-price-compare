from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

TEMPLATE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TEMPLATE_ROOT / "src"))

from price_monitor.compare import build_comparison  # noqa: E402
from price_monitor.config import load_config  # noqa: E402
from price_monitor.http_client import PoliteHttpClient  # noqa: E402
from price_monitor.parsers import collect_source  # noqa: E402
from price_monitor.sheets_output import (  # noqa: E402
    ALERTS_SHEET,
    ARCHIVE_SHEET,
    COMPARISON_SHEET,
    HISTORY_SHEET,
    RAW_SHEET,
    SINGLE_SHEET,
    SUMMARY_SHEET,
    TREND_SHEET,
    publish_to_sheets,
)


class WorksheetNotFound(Exception):
    pass


class FakeWorksheet:
    def __init__(self, sheet_id: int, title: str, rows: int, cols: int) -> None:
        self.id = sheet_id
        self.title = title
        self.row_count = rows
        self.col_count = cols
        self.values: list[list[Any]] = []
        self.updates: list[tuple[str, list[list[Any]], str]] = []

    def clear(self) -> None:
        self.values = []

    def resize(self, rows: int, cols: int) -> None:
        self.row_count = rows
        self.col_count = cols

    def update(self, values: list[list[Any]], range_name: str = "A1", value_input_option: str = "RAW") -> None:
        self.updates.append((range_name, values, value_input_option))
        if range_name == "A1":
            self.values = [list(r) for r in values]

    def get_values(self, _range: str) -> list[list[Any]]:
        return self.values[1:] if len(self.values) > 1 else []

    def get_all_values(self) -> list[list[Any]]:
        return [list(r) for r in self.values]


class FakeSpreadsheet:
    def __init__(self) -> None:
        self.title = ""
        self.worksheets: dict[str, FakeWorksheet] = {}
        self.batch_calls: list[dict[str, Any]] = []
        self._next_id = 1

    def update_title(self, title: str) -> None:
        self.title = title

    def worksheet(self, title: str) -> FakeWorksheet:
        if title not in self.worksheets:
            raise WorksheetNotFound(title)
        return self.worksheets[title]

    def add_worksheet(self, title: str, rows: int, cols: int) -> FakeWorksheet:
        ws = FakeWorksheet(self._next_id, title, rows, cols)
        self._next_id += 1
        self.worksheets[title] = ws
        return ws

    def del_worksheet(self, ws: FakeWorksheet) -> None:
        self.worksheets.pop(ws.title, None)

    def batch_update(self, body: dict[str, Any]) -> None:
        self.batch_calls.append(body)


class FakeGspreadClient:
    def __init__(self, spreadsheet: FakeSpreadsheet) -> None:
        self.spreadsheet = spreadsheet

    def open_by_key(self, _key: str) -> FakeSpreadsheet:
        return self.spreadsheet


def test_publish_to_sheets_creates_all_tabs_and_multi_day_sparklines() -> None:
    cfg = load_config(TEMPLATE_ROOT / "config.json")
    cfg.project.manual_update_url = "https://my-updater.example"
    client = PoliteHttpClient(cfg.safety, base_dir=cfg.config_dir)

    items = []
    for source in cfg.enabled_sources:
        items.extend(collect_source(source, cfg, client, fetched_at="2026-11-23T17:00:00+09:00"))
    compared, single, alerts = build_comparison(items, cfg)

    fake_sheet = FakeSpreadsheet()
    fake_sheet.add_worksheet("シート1", rows=10, cols=5)
    keep_ws = fake_sheet.add_worksheet("Sheet1", rows=10, cols=5)
    keep_ws.values = [["手動メモ"]]
    fake_client = FakeGspreadClient(fake_sheet)

    # 1日目実行
    url = publish_to_sheets(
        spreadsheet_id="DUMMY_SHEET_ID",
        credentials_file="dummy.json",
        config=cfg,
        items=items,
        compared_rows=compared,
        single_rows=single,
        alert_rows=alerts,
        fetched_at="2026-11-23T17:00:00+09:00",
        error_count=0,
        client_override=fake_client,
    )
    assert url == "https://docs.google.com/spreadsheets/d/DUMMY_SHEET_ID/edit"
    expected_tabs = {
        SUMMARY_SHEET,
        COMPARISON_SHEET,
        TREND_SHEET,
        ALERTS_SHEET,
        SINGLE_SHEET,
        HISTORY_SHEET,
        RAW_SHEET,
        ARCHIVE_SHEET,
    }
    assert expected_tabs.issubset(set(fake_sheet.worksheets))

    # 2日目実行（価格推移の前回比とSPARKLINEが生成されること）
    compared[0].best_price_yen -= 1000
    publish_to_sheets(
        spreadsheet_id="DUMMY_SHEET_ID",
        credentials_file="dummy.json",
        config=cfg,
        items=items,
        compared_rows=compared,
        single_rows=single,
        alert_rows=alerts,
        fetched_at="2026-11-24T17:00:00+09:00",
        error_count=0,
        client_override=fake_client,
    )

    # 履歴が2行蓄積され最新が先頭であること
    history_ws = fake_sheet.worksheets[HISTORY_SHEET]
    assert len(history_ws.values) == 3  # ヘッダー + 2日分
    assert history_ws.values[1][0].startswith("2026-11-24")
    assert history_ws.values[2][0].startswith("2026-11-23")

    # SPARKLINE数式が書き込まれていること
    trend_ws = fake_sheet.worksheets[TREND_SHEET]
    sparkline_updates = [u for u in trend_ws.updates if u[0].startswith("G2:")]
    assert sparkline_updates
    assert "SPARKLINE(" in sparkline_updates[-1][1][0][0]

    # サマリーに手動更新リンクと INDEX/MATCH 数式が入っていること
    summary_ws = fake_sheet.worksheets[SUMMARY_SHEET]
    flat_summary = " ".join(str(cell) for row in summary_ws.values for cell in row)
    assert "HYPERLINK(" in flat_summary
    assert "INDEX(更新履歴!" in flat_summary

    # 空の初期シート「シート1」は削除され、値入りシートは残ること
    assert "シート1" not in fake_sheet.worksheets
    assert "Sheet1" in fake_sheet.worksheets

    # 更新履歴A列・サマリーB3にDATE_TIME書式が適用され、価格推移の前回比にも色分けが入ること
    reqs = fake_sheet.batch_calls[-1]["requests"]
    has_history_dt = any(
        r.get("repeatCell", {}).get("range", {}).get("sheetId") == history_ws.id
        and r["repeatCell"]["range"].get("startColumnIndex") == 0
        and r["repeatCell"]["cell"]["userEnteredFormat"].get("numberFormat", {}).get("type") == "DATE_TIME"
        for r in reqs
    )
    has_summary_dt = any(
        r.get("repeatCell", {}).get("range", {}).get("sheetId") == summary_ws.id
        and r["repeatCell"]["range"].get("startRowIndex") == 2
        and r["repeatCell"]["range"].get("startColumnIndex") == 1
        and r["repeatCell"]["cell"]["userEnteredFormat"].get("numberFormat", {}).get("type") == "DATE_TIME"
        for r in reqs
    )
    has_trend_delta_color = any(
        r.get("repeatCell", {}).get("range", {}).get("sheetId") == trend_ws.id
        and r["repeatCell"]["range"].get("startColumnIndex") == 4
        and "foregroundColor" in r["repeatCell"]["cell"]["userEnteredFormat"].get("textFormat", {})
        for r in reqs
    )
    assert has_history_dt
    assert has_summary_dt
    assert has_trend_delta_color
