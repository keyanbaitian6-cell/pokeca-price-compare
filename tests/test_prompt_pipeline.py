from __future__ import annotations

import json

import gspread
import pandas as pd

from card_price_compare import cli
from card_price_compare.google_output import (
    COMPARISON_SHEET_TITLE,
    HISTORY_HEADERS,
    HISTORY_SHEET_TITLE,
    NO_SHRINK_SHEET_TITLE,
    PROMPT_SHEET_TITLE,
    RAW_SHEET_TITLE,
    SINGLE_LISTING_SHEET_TITLE,
    STORE_GUIDE_SHEET_TITLE,
    SUMMARY_COUNTER_ROWS,
    SUMMARY_SHEET_TITLE,
    TREND_ARCHIVE_SHEET_TITLE,
    TREND_HEADERS,
    TREND_SHEET_TITLE,
    publish_frames,
)
from card_price_compare.prompt_builder import PROMPT_SHEET_HEADERS, find_leaked_store_terms


class _FakeWorksheet:
    def __init__(
        self,
        sheet_id: int,
        title: str,
        initial_rows: list[list[object]] | None = None,
    ) -> None:
        self.id = sheet_id
        self.title = title
        self.row_count = 30
        self.col_count = 15
        self.initial_rows = initial_rows or []
        self.updates: list[tuple[str, list[list[object]], str]] = []
        self.a1_value: str | None = None
        self.cleared = False

    def get_values(self, range_name: str, **_kwargs: object) -> list[list[object]]:
        if range_name == "A1:F1":
            return self.initial_rows[:1]
        if range_name == "A2:G":
            return self.initial_rows[1:]
        if range_name == "A10:B16":
            return []
        return self.initial_rows

    def clear(self) -> None:
        self.cleared = True

    def resize(self, *, rows: int, cols: int) -> None:
        self.row_count = rows
        self.col_count = cols

    def update(
        self,
        *,
        values: list[list[object]],
        range_name: str,
        value_input_option: str,
    ) -> None:
        self.updates.append((range_name, values, value_input_option))

    def update_acell(self, cell: str, value: str) -> None:
        if cell == "A1":
            self.a1_value = value


class _FakeSpreadsheet:
    def __init__(self, worksheets: dict[str, _FakeWorksheet]) -> None:
        self.worksheets = worksheets
        self.batches: list[dict[str, object]] = []
        self.title = ""
        self._next_id = 900

    def update_title(self, title: str) -> None:
        self.title = title

    def worksheet(self, title: str) -> _FakeWorksheet:
        if title not in self.worksheets:
            raise gspread.WorksheetNotFound(title)
        return self.worksheets[title]

    def add_worksheet(self, *, title: str, rows: int, cols: int) -> _FakeWorksheet:
        ws = _FakeWorksheet(self._next_id, title)
        ws.row_count = rows
        ws.col_count = cols
        self._next_id += 1
        self.worksheets[title] = ws
        return ws

    def fetch_sheet_metadata(self, **_kwargs: object) -> dict[str, object]:
        return {"sheets": []}

    def batch_update(self, body: dict[str, object]) -> None:
        self.batches.append(body)


def test_publish_frames_adds_prompt_tab_without_breaking_existing_tabs_or_cell_positions(
    monkeypatch, tmp_path
) -> None:
    archive_ws = _FakeWorksheet(
        200,
        TREND_ARCHIVE_SHEET_TITLE,
        [
            TREND_HEADERS,
            ["2026-11-17", "151", 20_000, "runto"],
            ["2026-11-23", "151", 22_000, "runto"],
            ["2026-11-17", "ステラミラクル", 13_000, "runto"],
            ["2026-11-23", "ステラミラクル", 12_500, "runto"],
        ],
    )
    summary_ws = _FakeWorksheet(100, SUMMARY_SHEET_TITLE)
    spreadsheet = _FakeSpreadsheet(
        {
            SUMMARY_SHEET_TITLE: summary_ws,
            TREND_ARCHIVE_SHEET_TITLE: archive_ws,
        }
    )

    class _FakeClient:
        def open_by_key(self, _sheet_id: str) -> _FakeSpreadsheet:
            return spreadsheet

    monkeypatch.setattr(gspread, "service_account", lambda **_kwargs: _FakeClient())

    raw = pd.DataFrame(
        [
            {
                "source": "runto",
                "product_name_raw": "ポケモンカード151 シュリンク付",
                "product_name_normalized": "151",
                "match_key": "151|shrink_wrapped",
                "variant": "シュリンク付",
                "condition": "shrink_wrapped",
                "product_kind": "sealed_box",
                "price_yen": 24_000,
                "price_min_yen": 24_000,
                "price_max_yen": 24_000,
                "stock_status": "active",
                "product_url": "https://runto666.com/151",
                "source_updated_label": "",
                "fetched_at": "2026-11-24T17:00:00+09:00",
                "notes": "",
            },
            {
                "source": "somurie",
                "product_name_raw": "ポケモンカード151 シュリンク付きボックス",
                "product_name_normalized": "151",
                "match_key": "151|shrink_wrapped",
                "variant": "",
                "condition": "shrink_wrapped",
                "product_kind": "sealed_box",
                "price_yen": 22_500,
                "price_min_yen": 22_500,
                "price_max_yen": 22_500,
                "stock_status": "active",
                "product_url": "https://somurie-kaitori.com/151",
                "source_updated_label": "",
                "fetched_at": "2026-11-24T17:00:00+09:00",
                "notes": "",
            },
            {
                "source": "runto",
                "product_name_raw": "ステラミラクル シュリンク付",
                "product_name_normalized": "ステラミラクル",
                "match_key": "ステラミラクル|shrink_wrapped",
                "variant": "シュリンク付",
                "condition": "shrink_wrapped",
                "product_kind": "sealed_box",
                "price_yen": 11_800,
                "price_min_yen": 11_800,
                "price_max_yen": 11_800,
                "stock_status": "active",
                "product_url": "https://runto666.com/stella",
                "source_updated_label": "",
                "fetched_at": "2026-11-24T17:00:00+09:00",
                "notes": "",
            },
            {
                "source": "somurie",
                "product_name_raw": "ステラミラクル シュリンク付きボックス",
                "product_name_normalized": "ステラミラクル",
                "match_key": "ステラミラクル|shrink_wrapped",
                "variant": "",
                "condition": "shrink_wrapped",
                "product_kind": "sealed_box",
                "price_yen": 8_000,
                "price_min_yen": 8_000,
                "price_max_yen": 8_000,
                "stock_status": "active",
                "product_url": "https://somurie-kaitori.com/stella",
                "source_updated_label": "",
                "fetched_at": "2026-11-24T17:00:00+09:00",
                "notes": "",
            },
        ]
    )
    comparison = pd.DataFrame(
        [
            {
                "product_name_normalized": "151",
                "condition": "shrink_wrapped",
                "condition_inferred": False,
                "collect_price_yen": pd.NA,
                "runto_price_yen": 24_000,
                "somurie_price_yen": 22_500,
                "best_site": "runto",
                "best_price_yen": 24_000,
                "spread_yen": 1_500,
                "matched_site_count": 2,
                "collect_name": pd.NA,
                "runto_name": "ポケモンカード151 シュリンク付",
                "somurie_name": "ポケモンカード151 シュリンク付きボックス",
            },
            {
                "product_name_normalized": "ステラミラクル",
                "condition": "shrink_wrapped",
                "condition_inferred": False,
                "collect_price_yen": pd.NA,
                "runto_price_yen": 11_800,
                "somurie_price_yen": 8_000,
                "best_site": "runto",
                "best_price_yen": 11_800,
                "spread_yen": 3_800,
                "matched_site_count": 2,
                "collect_name": pd.NA,
                "runto_name": "ステラミラクル シュリンク付",
                "somurie_name": "ステラミラクル シュリンク付きボックス",
            },
        ]
    )
    web_json = tmp_path / "market_index.json"

    url = publish_frames(
        spreadsheet_id="output-sheet-id",
        credentials_file=tmp_path / "dummy.json",
        comparison=comparison,
        raw=raw,
        fetched_at="2026-11-24T17:00:00+09:00",
        error_count=0,
        prompt_output_dir=tmp_path,
        web_market_json_path=web_json,
    )

    assert url == "https://docs.google.com/spreadsheets/d/output-sheet-id/edit"

    # Existing tabs remain completely intact with dynamic store columns
    comp_ws = spreadsheet.worksheets[COMPARISON_SHEET_TITLE]
    assert comp_ws.updates[0][1][0] == [
        "シリーズ",
        "商品名",
        "最高値",
        "前回比",
        "最高値の店",
        "差率",
        "差額",
        "定価比",
        "runto",
        "買取ソムリエ",
        "注意",
    ]
    hist_ws = spreadsheet.worksheets[HISTORY_SHEET_TITLE]
    assert hist_ws.updates[0][1][0] == HISTORY_HEADERS
    assert [rng for rng, _, _ in summary_ws.updates] == ["A3", "A9", "C9", "A10"]
    assert summary_ws.updates[0][1] == SUMMARY_COUNTER_ROWS
    assert summary_ws.updates[3][1][1][0] == "価格取得元"
    assert NO_SHRINK_SHEET_TITLE in spreadsheet.worksheets
    assert STORE_GUIDE_SHEET_TITLE in spreadsheet.worksheets

    # Public anonymized web market JSON is exported with full archive history and zero store leaks
    web_text = web_json.read_text(encoding="utf-8")
    assert find_leaked_store_terms(web_text) == []
    web_payload = json.loads(web_text)
    assert web_payload["anonymized"] is True
    assert web_payload["summary"]["history_days"] == 3
    assert len(web_payload["items"]) == 2

    # New 発信プロンプト tab is populated via RAW with multi-day archive insights
    prompt_ws = spreadsheet.worksheets[PROMPT_SHEET_TITLE]
    assert len(prompt_ws.updates) == 1
    range_name, rows, input_option = prompt_ws.updates[0]
    assert range_name == "A1"
    assert input_option == "RAW"
    assert rows[0] == PROMPT_SHEET_HEADERS
    assert len(rows) == 8  # header + 7 entries

    prompt_sheet_blob = "\n".join(str(cell) for row in rows for cell in row)
    # Multi-day deltas from archive sheet (151: +2,000 prev, +4,000 7d; ステラミラクル: -700 prev)
    assert "+2,000円" in prompt_sheet_blob
    assert "+4,000円" in prompt_sheet_blob
    assert "-700円" in prompt_sheet_blob
    assert "32.2%" in prompt_sheet_blob
    assert "https://keyanbaitian6-cell.github.io/pokeca-price-compare/" in prompt_sheet_blob
    # Zero store name leakage inside 発信プロンプト
    assert find_leaked_store_terms(prompt_sheet_blob) == []

    # Tab ordering keeps visible tabs clean and archive hidden at the end
    reorder_batch = spreadsheet.batches[-1]["requests"]
    id_to_title = {ws.id: title for title, ws in spreadsheet.worksheets.items()}
    ordered = [
        (
            id_to_title[req["updateSheetProperties"]["properties"]["sheetId"]],
            req["updateSheetProperties"]["properties"]["index"],
            req["updateSheetProperties"]["properties"]["hidden"],
        )
        for req in reorder_batch
        if "updateSheetProperties" in req
    ]
    assert ordered == [
        (SUMMARY_SHEET_TITLE, 0, False),
        (COMPARISON_SHEET_TITLE, 1, False),
        (NO_SHRINK_SHEET_TITLE, 2, False),
        (TREND_SHEET_TITLE, 3, False),
        (SINGLE_LISTING_SHEET_TITLE, 4, False),
        (STORE_GUIDE_SHEET_TITLE, 5, False),
        (HISTORY_SHEET_TITLE, 6, False),
        (RAW_SHEET_TITLE, 7, False),
        (PROMPT_SHEET_TITLE, 8, False),
        (TREND_ARCHIVE_SHEET_TITLE, 9, True),
    ]

    # Local artifacts in prompt_output_dir are refreshed using the archive history too
    insights_json = json.loads((tmp_path / "market_insights.json").read_text(encoding="utf-8"))
    assert insights_json["history_days_available"] == 3
    assert insights_json["week_gainers"][0]["product_name"] == "151"
    assert (tmp_path / "ai_prompts.md").exists()
    assert (tmp_path / "ai_prompts.json").exists()


def test_cli_from_local_data_regenerates_prompts_with_zero_network_calls(
    monkeypatch, tmp_path
) -> None:
    def _fail_if_called(*_args, **_kwargs):
        raise AssertionError("Scraping must not be invoked in --from-local-data mode")

    monkeypatch.setattr(cli, "fetch_homura_records", _fail_if_called)
    monkeypatch.setattr(cli, "fetch_tcgpro_records", _fail_if_called)
    monkeypatch.setattr(cli, "fetch_morimori_records", _fail_if_called)
    monkeypatch.setattr(cli, "fetch_rudeya_records", _fail_if_called)
    monkeypatch.setattr(cli, "fetch_runto_records", _fail_if_called)
    monkeypatch.setattr(cli, "fetch_somurie_records", _fail_if_called)
    monkeypatch.setattr(cli, "fetch_collect_records", _fail_if_called)

    pd.DataFrame(
        [
            {
                "product_name_normalized": "イーブイヒーローズ",
                "condition": "shrink_wrapped",
                "condition_inferred": False,
                "best_price_yen": 135_000,
                "spread_yen": 5_000,
                "matched_site_count": 2,
            }
        ]
    ).to_csv(tmp_path / "box_comparison.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(
        [
            ["2026-11-17", "イーブイヒーローズ", 125_000, "runto"],
            ["2026-11-23", "イーブイヒーローズ", 130_000, "runto"],
            ["2026-11-24", "イーブイヒーローズ", 135_000, "買取ソムリエ"],
        ],
        columns=TREND_HEADERS,
    ).to_csv(tmp_path / "shrink_trend_history.csv", index=False, encoding="utf-8-sig")

    web_json = tmp_path / "market.json"
    rc = cli.main(
        ["--from-local-data", "--output-dir", str(tmp_path), "--web-market-json", str(web_json)]
    )
    assert rc == 0

    md = (tmp_path / "ai_prompts.md").read_text(encoding="utf-8")
    assert "イーブイヒーローズ" in md
    assert "+5,000円" in md
    assert "+10,000円" in md
    assert find_leaked_store_terms(md) == []
    assert web_json.exists()
    assert find_leaked_store_terms(web_json.read_text(encoding="utf-8")) == []


def test_cli_normal_run_persists_local_trend_and_generates_prompts(
    monkeypatch, tmp_path
) -> None:
    from card_price_compare.models import PriceRecord

    def _fake_runto(_requester, *, fetched_at: str, **_kwargs):
        return [
            PriceRecord(
                source="runto",
                product_name_raw="ポケモンカード151 シュリンク付",
                product_name_normalized="151",
                match_key="151|shrink_wrapped",
                variant="シュリンク付",
                condition="shrink_wrapped",
                product_kind="sealed_box",
                price_yen=24_000,
                price_min_yen=24_000,
                price_max_yen=24_000,
                stock_status="active",
                product_url="https://runto666.com/151",
                source_updated_label="",
                fetched_at=fetched_at,
            )
        ]

    def _fake_somurie(*, fetched_at: str, **_kwargs):
        return [
            PriceRecord(
                source="somurie",
                product_name_raw="ポケモンカード151 シュリンク付きボックス",
                product_name_normalized="151",
                match_key="151|shrink_wrapped",
                variant="",
                condition="shrink_wrapped",
                product_kind="sealed_box",
                price_yen=22_000,
                price_min_yen=22_000,
                price_max_yen=22_000,
                stock_status="active",
                product_url="https://somurie-kaitori.com/151",
                source_updated_label="",
                fetched_at=fetched_at,
            )
        ]

    monkeypatch.setattr(cli, "fetch_runto_records", _fake_runto)
    monkeypatch.setattr(cli, "fetch_somurie_records", _fake_somurie)

    # Seed a prior day in local trend history
    pd.DataFrame(
        [["2026-11-10", "151", 20_000, "runto"]],
        columns=TREND_HEADERS,
    ).to_csv(tmp_path / "shrink_trend_history.csv", index=False, encoding="utf-8-sig")

    rc = cli.main(["--sources", "runto,somurie", "--output-dir", str(tmp_path)])
    assert rc == 0

    assert (tmp_path / "raw_prices.csv").exists()
    assert (tmp_path / "box_comparison.csv").exists()
    assert (tmp_path / "shrink_trend_history.csv").exists()
    assert (tmp_path / "market_insights.json").exists()
    assert (tmp_path / "ai_prompts.json").exists()
    assert (tmp_path / "ai_prompts.md").exists()

    summary = json.loads((tmp_path / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["record_count"] == 2
    assert summary["comparison_count"] == 1
    assert summary["errors"] == {}
    assert summary["prompt_files"]["ai_prompts_md"] == "ai_prompts.md"
    assert summary["market_sentiment"]["prev_up_count"] == 1

    trend_saved = pd.read_csv(tmp_path / "shrink_trend_history.csv", encoding="utf-8-sig")
    assert len(trend_saved) == 2

    # --skip-prompts leaves existing CSV pipeline intact without writing prompt artifacts
    skip_dir = tmp_path / "skip_run"
    rc_skip = cli.main(
        ["--sources", "runto,somurie", "--output-dir", str(skip_dir), "--skip-prompts"]
    )
    assert rc_skip == 0
    assert (skip_dir / "box_comparison.csv").exists()
    assert not (skip_dir / "ai_prompts.md").exists()

