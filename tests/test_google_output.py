import gspread
import pandas as pd
import pytest
from gspread.utils import ValueRenderOption

from card_price_compare.collectors.collect_sheet import SPREADSHEET_ID
from card_price_compare.google_output import (
    COMPARISON_COLUMNS,
    COMPARISON_HEADER_NOTES_BY_NAME,
    HISTORY_HEADERS,
    MANUAL_UPDATE_FORMULA,
    MANUAL_UPDATE_URL,
    NO_SHRINK_COLUMNS,
    SINGLE_LISTING_COLUMNS,
    SPREADSHEET_TITLE,
    STORE_GUIDE_COLUMNS,
    SUMMARY_COUNTER_LIMIT,
    SUMMARY_COUNTER_ROWS,
    TREND_ARCHIVE_SHEET_TITLE,
    TREND_FIXED_COLUMNS,
    TREND_HEADERS,
    TREND_SHEET_TITLE,
    _comparison_format_requests,
    _comparison_sheet_frame,
    _ensure_summary_sheet,
    _history_backfill_updates,
    _history_row,
    _merge_trend_history,
    _no_shrink_format_requests,
    _no_shrink_sheet_frame,
    _prepare_history_rows,
    _publish_shrink_trends,
    _raw_sheet_frame,
    _row_runs,
    _shrink_trend_frame,
    _single_listing_sheet_frame,
    _store_guide_sheet_frame,
    _store_label,
    _trend_history_frame,
    _trend_matrix_frame,
    _trend_sparkline_formula,
    publish_frames,
    split_comparison,
)


def _comparison_record(
    name: str,
    condition: str,
    *,
    collect: int | None = None,
    runto: int | None = None,
    somurie: int | None = None,
    inferred: bool = False,
) -> dict[str, object]:
    prices = {"collect": collect, "runto": runto, "somurie": somurie}
    present = {source: price for source, price in prices.items() if price is not None}
    best_price = max(present.values())
    best_site = ",".join(source for source, price in present.items() if price == best_price)
    spread = best_price - min(present.values()) if len(present) >= 2 else None
    return {
        "product_name_normalized": name,
        "condition": condition,
        "condition_inferred": inferred,
        "collect_price_yen": collect,
        "runto_price_yen": runto,
        "somurie_price_yen": somurie,
        "best_site": best_site,
        "best_price_yen": best_price,
        "spread_yen": spread,
        "matched_site_count": len(present),
    }


@pytest.fixture
def comparison() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _comparison_record("ステラミラクル", "no_shrink", collect=8_000, runto=11_800),
            _comparison_record(
                "白銀のランス", "shrink_wrapped", collect=17_000, runto=17_500, inferred=True
            ),
            _comparison_record(
                "ストームエメラルダ",
                "shrink_wrapped",
                collect=18_000,
                runto=18_000,
                somurie=18_000,
            ),
            _comparison_record("第1弾", "unspecified", runto=13_000_000),
            _comparison_record("e 基本 海からの風", "unspecified", collect=500),
        ]
    )


def test_manual_update_link_points_to_vercel_page() -> None:
    assert MANUAL_UPDATE_URL == "https://pokeca-price-update.vercel.app"
    assert MANUAL_UPDATE_URL in MANUAL_UPDATE_FORMULA
    assert "価格表を手動更新" in MANUAL_UPDATE_FORMULA


def test_trend_history_refuses_to_overwrite_an_unrecognized_table() -> None:
    with pytest.raises(ValueError, match="既存データを保護"):
        _trend_history_frame([["別の列", "商品名", "最高値", "最高値の店"]])


def test_trend_history_keeps_a_currency_formatted_previous_price() -> None:
    headers = ["日付", "商品名", "最高値", "最高値の店"]
    existing = pd.DataFrame([["2026-08-24", "151", "¥55,000", "runto"]], columns=headers)
    current = pd.DataFrame([["2026-08-25", "151", 56_000, "コレクト"]], columns=headers)

    merged = _merge_trend_history(existing, current)

    assert merged.to_dict("records") == [
        {"日付": "2026-08-24", "商品名": "151", "最高値": 55_000, "最高値の店": "runto"},
        {"日付": "2026-08-25", "商品名": "151", "最高値": 56_000, "最高値の店": "コレクト"},
    ]


def test_merge_trend_history_normalizes_split_set_code_names_and_prefers_current_store() -> None:
    existing = pd.DataFrame(
        [
            ["2026-10-01", "テラスタルフェスex sv8a", 12_500, "買取ソムリエ"],
            ["2026-10-01", "テラスタルフェスex", 12_000, "コレクト"],
            ["2026-10-02", "テラスタルフェスex", 12_500, "コレクト"],
        ],
        columns=TREND_HEADERS,
    )
    current = pd.DataFrame(
        [["2026-10-02", "テラスタルフェスex", 12_500, "コレクト・買取ソムリエ"]],
        columns=TREND_HEADERS,
    )

    merged = _merge_trend_history(existing, current)

    assert merged.to_dict("records") == [
        {
            "日付": "2026-10-01",
            "商品名": "テラスタルフェスex",
            "最高値": 12_500,
            "最高値の店": "買取ソムリエ",
        },
        {
            "日付": "2026-10-02",
            "商品名": "テラスタルフェスex",
            "最高値": 12_500,
            "最高値の店": "コレクト・買取ソムリエ",
        },
    ]


def test_shrink_trend_frame_uses_raw_explicit_shrink_wrapped_when_comparison_is_inferred(
    comparison: pd.DataFrame,
) -> None:
    raw = pd.DataFrame(
        [
            {
                "source": "collect",
                "product_name_normalized": "白銀のランス",
                "condition": "shrink_wrapped",
                "product_kind": "sealed_box",
                "price_yen": 17_000,
                "stock_status": "active",
            },
            {
                "source": "runto",
                "product_name_normalized": "白銀のランス",
                "condition": "unspecified",
                "product_kind": "sealed_box",
                "price_yen": 17_500,
                "stock_status": "active",
            },
        ]
    )

    trend = _shrink_trend_frame(
        comparison, fetched_at="2026-08-25T17:00:00+09:00", raw=raw
    )

    assert trend.to_dict("records") == [
        {
            "日付": "2026-08-25",
            "商品名": "白銀のランス",
            "最高値": 17_000,
            "最高値の店": "コレクト",
        }
    ]


def test_trend_matrix_frame_orders_moving_boxes_first_and_computes_deltas() -> None:
    history = pd.DataFrame(
        [
            ["2026-10-01", "安定BOX", 20_000, "コレクト"],
            ["2026-10-08", "安定BOX", 20_000, "コレクト"],
            ["2026-10-09", "安定BOX", 20_000, "コレクト"],
            ["2026-10-01", "急騰BOX", 10_000, "runto"],
            ["2026-10-08", "急騰BOX", 11_000, "runto"],
            ["2026-10-09", "急騰BOX", 12_500, "買取ソムリエ"],
            ["2026-09-01", "古い絶版BOX", 30_000, "コレクト"],
        ],
        columns=TREND_HEADERS,
    )

    matrix = _trend_matrix_frame(history)

    assert list(matrix.columns) == TREND_FIXED_COLUMNS + ["10/09", "10/08", "10/01", "09/01"]
    assert list(matrix["商品名"]) == ["急騰BOX", "安定BOX"]
    top = matrix.iloc[0]
    assert top["最新最高値"] == 12_500
    assert top["最高値の店"] == "買取ソムリエ"
    assert top["前回比"] == 1_500
    assert top["7日前比"] == 2_500
    assert top["10/09"] == 12_500
    assert top["10/08"] == 11_000
    assert top["09/01"] == ""


def test_trend_sparkline_formula_plots_chronologically() -> None:
    formula = _trend_sparkline_formula(row_number=2, num_dates=4)
    assert "G2:J2" in formula
    assert "SEQUENCE(4)" in formula
    assert "FALSE" in formula
    assert _trend_sparkline_formula(row_number=2, num_dates=1) == ""


def test_trend_publish_migrates_legacy_sheet_to_hidden_archive_and_renders_matrix(
    comparison: pd.DataFrame,
) -> None:
    class FakeWorksheet:
        def __init__(
            self,
            sheet_id: int,
            title: str,
            initial_rows: list[list[object]] | None = None,
        ) -> None:
            self.id = sheet_id
            self.title = title
            self.row_count = 3000
            self.col_count = 25
            self.initial_rows = initial_rows or []
            self.value_render_options: list[object] = []
            self.updates: list[tuple[str, list[list[object]], str]] = []
            self.cleared = False
            self.resized_to: tuple[int, int] | None = None

        def get_values(self, _range: str, *, value_render_option: ValueRenderOption):
            self.value_render_options.append(value_render_option)
            if _range == "A1:F1":
                return self.initial_rows[:1]
            return self.initial_rows

        def clear(self) -> None:
            self.cleared = True

        def update(
            self,
            *,
            values: list[list[object]],
            range_name: str,
            value_input_option: str,
        ) -> None:
            self.updates.append((range_name, values, value_input_option))

        def resize(self, *, rows: int, cols: int) -> None:
            self.row_count = rows
            self.col_count = cols
            self.resized_to = (rows, cols)

    class FakeSpreadsheet:
        def __init__(self, worksheets: dict[str, FakeWorksheet]) -> None:
            self.worksheets = worksheets
            self.batches: list[dict[str, object]] = []
            self._next_id = 500

        def worksheet(self, title: str) -> FakeWorksheet:
            if title not in self.worksheets:
                raise gspread.WorksheetNotFound(title)
            return self.worksheets[title]

        def add_worksheet(self, *, title: str, rows: int, cols: int) -> FakeWorksheet:
            ws = FakeWorksheet(self._next_id, title)
            ws.row_count = rows
            ws.col_count = cols
            self._next_id += 1
            self.worksheets[title] = ws
            return ws

        def fetch_sheet_metadata(self, **_kwargs: object) -> dict[str, object]:
            return {"sheets": [{"properties": {"sheetId": 123}, "charts": [{"chartId": 999}]}]}

        def batch_update(self, body: dict[str, object]) -> None:
            self.batches.append(body)

    legacy_trend_ws = FakeWorksheet(
        123,
        TREND_SHEET_TITLE,
        [
            ["日付", "商品名", "最高値", "最高値の店"],
            ["2026-08-24", "ストームエメラルダ", 17_000, "runto"],
        ],
    )
    fake_spreadsheet = FakeSpreadsheet({TREND_SHEET_TITLE: legacy_trend_ws})

    previous_prices = _publish_shrink_trends(
        fake_spreadsheet,
        comparison,
        fetched_at="2026-08-25T17:00:00+09:00",
    )

    assert all(
        opt == ValueRenderOption.unformatted for opt in legacy_trend_ws.value_render_options
    )
    archive_ws = fake_spreadsheet.worksheets[TREND_ARCHIVE_SHEET_TITLE]
    assert archive_ws.updates[0][1] == [
        ["日付", "商品名", "最高値", "最高値の店"],
        ["2026-08-24", "ストームエメラルダ", 17_000, "runto"],
        ["2026-08-25", "ストームエメラルダ", 18_000, "3店同額"],
    ]
    assert legacy_trend_ws.cleared is True
    matrix_values = legacy_trend_ws.updates[0][1]
    assert matrix_values[0] == TREND_FIXED_COLUMNS + ["08/25", "08/24"]
    assert matrix_values[1][:5] == ["ストームエメラルダ", 18_000, "3店同額", 1_000, ""]
    assert matrix_values[1][6:] == [18_000, 17_000]
    assert legacy_trend_ws.updates[1][0] == "F2:F2"
    assert legacy_trend_ws.updates[1][2] == "USER_ENTERED"
    assert "SPARKLINE" in str(legacy_trend_ws.updates[1][1][0][0])

    # Legacy chart 999 was deleted before resizing, and archive sheet was hidden.
    all_requests = [req for batch in fake_spreadsheet.batches for req in batch["requests"]]
    assert {"deleteEmbeddedObject": {"objectId": 999}} in all_requests
    assert {
        "updateSheetProperties": {
            "properties": {"sheetId": archive_ws.id, "hidden": True},
            "fields": "hidden",
        }
    } in all_requests
    assert previous_prices == {"ストームエメラルダ": 17_000}


def test_collect_source_sheet_cannot_be_output_target(tmp_path) -> None:
    with pytest.raises(ValueError, match="参照元"):
        publish_frames(
            spreadsheet_id=SPREADSHEET_ID,
            credentials_file=tmp_path / "not-used.json",
            comparison=pd.DataFrame(),
            raw=pd.DataFrame(),
        )


def test_single_site_rows_move_out_of_the_comparison_tab(comparison: pd.DataFrame) -> None:
    multi_site, single_site = split_comparison(comparison)

    assert len(multi_site) == 3
    assert list(single_site["product_name_normalized"]) == ["第1弾", "e 基本 海からの風"]


def test_comparison_tab_uses_dynamic_store_columns_and_series_msrp_ratio(
    comparison: pd.DataFrame,
) -> None:
    prepared = _comparison_sheet_frame(comparison)

    assert list(prepared.columns) == [
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
        "コレクト",
        "注意",
    ]
    assert len(prepared) == 2
    assert "ステラミラクル" not in prepared["商品名"].tolist()
    assert prepared.loc[prepared["商品名"] == "白銀のランス", "シリーズ"].iloc[0] == "S&S"
    assert prepared.loc[prepared["商品名"] == "白銀のランス", "定価比"].iloc[0] == pytest.approx(
        round(17_500 / 4_950, 2)
    )
    # The original store names stay on the raw tab instead of widening this one.
    assert "runto商品名" not in prepared.columns


def test_no_shrink_tab_computes_shrink_penalty_against_shrink_wrapped_peak() -> None:
    df = pd.DataFrame(
        [
            _comparison_record("151", "shrink_wrapped", collect=40_000, runto=42_000),
            _comparison_record("151", "no_shrink", collect=35_000, runto=37_000),
        ]
    )
    prepared = _no_shrink_sheet_frame(df)

    assert list(prepared.columns) == [
        "シリーズ",
        "商品名",
        "シュリンク無最高値",
        "最高値の店",
        "シュリンク有最高値",
        "有無差額",
        "有無差率",
        "runto",
        "コレクト",
    ]
    row = prepared.iloc[0]
    assert row["シリーズ"] == "SV"
    assert row["シュリンク無最高値"] == 37_000
    assert row["シュリンク有最高値"] == 42_000
    assert row["有無差額"] == 5_000
    assert row["有無差率"] == pytest.approx(round(5_000 / 42_000, 6))
    reqs = _no_shrink_format_requests(99, prepared)
    assert any("setBasicFilter" in req for req in reqs)


def test_store_guide_tab_reflects_active_and_paused_stores() -> None:
    raw = pd.DataFrame({"source": ["homura", "homura", "runto"]})
    guide = _store_guide_sheet_frame(raw)

    assert list(guide.columns) == STORE_GUIDE_COLUMNS
    by_name = guide.set_index("店舗名")
    assert by_name.loc["買取ホムラ", "取得状態"] == "稼働中"
    assert by_name.loc["買取ホムラ", "今回取得件数"] == 2
    assert by_name.loc["コレクト", "取得状態"] == "一時中断"


def test_comparison_tab_computes_previous_price_deltas(comparison: pd.DataFrame) -> None:
    prepared = _comparison_sheet_frame(
        comparison,
        previous_prices={"ストームエメラルダ": 17_200},
    )

    by_name = prepared.set_index("商品名")
    assert by_name.loc["ストームエメラルダ", "前回比"] == 800
    assert by_name.loc["白銀のランス", "前回比"] == ""


def test_comparison_tab_is_sorted_by_spread_rate(comparison: pd.DataFrame) -> None:
    prepared = _comparison_sheet_frame(comparison)

    assert list(prepared["商品名"]) == ["白銀のランス", "ストームエメラルダ"]
    assert prepared.iloc[0]["差額"] == 500
    assert prepared.iloc[0]["差率"] == pytest.approx(round(500 / 17_500, 6))
    assert prepared.iloc[1]["差率"] == 0.0


def test_comparison_tab_names_the_best_store_in_japanese(comparison: pd.DataFrame) -> None:
    prepared = _comparison_sheet_frame(comparison)

    assert prepared.iloc[0]["最高値の店"] == "runto"
    assert prepared.iloc[0]["最高値"] == 17_500
    assert prepared.iloc[1]["最高値の店"] == "3店同額"


def test_tied_best_stores_are_joined_with_a_middle_dot() -> None:
    assert _store_label("collect") == "コレクト"
    assert _store_label("collect,runto") == "コレクト・runto"
    assert _store_label("collect,somurie") == "コレクト・買取ソムリエ"
    assert _store_label("collect,runto,somurie") == "3店同額"
    assert _store_label("homura,tcgpro,morimori,runto") == "4店同額"
    assert _store_label("") == ""


def test_inferred_condition_is_flagged_in_the_warning_column(comparison: pd.DataFrame) -> None:
    prepared = _comparison_sheet_frame(comparison)

    assert prepared.iloc[0]["商品名"] == "白銀のランス"
    assert prepared.iloc[0]["注意"] == "状態推定"
    assert prepared.iloc[1]["注意"] == ""


def test_single_listing_tab_lists_one_store_rows_by_price(comparison: pd.DataFrame) -> None:
    prepared = _single_listing_sheet_frame(comparison)

    assert list(prepared.columns) == SINGLE_LISTING_COLUMNS
    assert list(prepared["商品名"]) == ["第1弾", "e 基本 海からの風"]
    assert list(prepared["掲載店"]) == ["runto", "コレクト"]
    assert prepared.iloc[0]["買取価格"] == 13_000_000
    assert prepared.iloc[0]["状態"] == "状態不明"


def test_empty_comparison_still_produces_all_tab_layouts() -> None:
    empty = pd.DataFrame()

    assert list(_comparison_sheet_frame(empty).columns) == COMPARISON_COLUMNS
    assert list(_no_shrink_sheet_frame(empty).columns) == NO_SHRINK_COLUMNS
    assert list(_single_listing_sheet_frame(empty).columns) == SINGLE_LISTING_COLUMNS


def test_google_sheet_conditions_are_localized_without_changing_internal_codes() -> None:
    raw = pd.DataFrame(
        {
            "condition": [
                "shrink_wrapped",
                "no_shrink",
                "no_perforation",
                "unspecified",
                "sealed_unspecified",
            ]
        }
    )

    assert _raw_sheet_frame(raw)["状態"].tolist() == [
        "シュリンク有",
        "シュリンク無",
        "ぺりぺり無",
        "状態不明",
        "未開封（状態不明）",
    ]
    assert raw["condition"].tolist()[0] == "shrink_wrapped"


def test_row_runs_collapse_adjacent_rows() -> None:
    assert _row_runs([True, True, False, True]) == [(0, 2), (3, 4)]
    assert _row_runs([False, False]) == []


GREEN = {"red": 198 / 255, "green": 239 / 255, "blue": 206 / 255}
RED = {"red": 192 / 255, "green": 0.0, "blue": 0.0}
GOLD = {"red": 191 / 255, "green": 143 / 255, "blue": 0.0}
YELLOW = {"red": 1.0, "green": 242 / 255, "blue": 204 / 255}
UP_GREEN = {"red": 19 / 255, "green": 115 / 255, "blue": 51 / 255}
DOWN_BLUE = {"red": 25 / 255, "green": 103 / 255, "blue": 210 / 255}


def _ranges_with_background(requests: list[dict], color: dict) -> list[dict]:
    return [
        request["repeatCell"]["range"]
        for request in requests
        if "repeatCell" in request
        and request["repeatCell"]["cell"].get("userEnteredFormat", {}).get("backgroundColor")
        == color
    ]


def _cell_range(sheet_id: int, rows: tuple[int, int], column: int) -> dict:
    return {
        "sheetId": sheet_id,
        "startRowIndex": rows[0],
        "endRowIndex": rows[1],
        "startColumnIndex": column,
        "endColumnIndex": column + 1,
    }


def test_comparison_formatting_highlights_the_best_price_cells(
    comparison: pd.DataFrame,
) -> None:
    prepared = _comparison_sheet_frame(comparison)
    requests = _comparison_format_requests(123, prepared)
    cols = list(prepared.columns)

    # runto wins row 1; row 2 is a three-way tie, so all three store columns go green.
    assert _ranges_with_background(requests, GREEN) == [
        _cell_range(123, (1, 3), cols.index("runto")),
        _cell_range(123, (2, 3), cols.index("買取ソムリエ")),
        _cell_range(123, (2, 3), cols.index("コレクト")),
    ]


def test_comparison_formatting_marks_high_spread_rates_deltas_and_warnings() -> None:
    prepared = _comparison_sheet_frame(
        pd.DataFrame(
            [
                _comparison_record(
                    "ステラミラクル", "shrink_wrapped", collect=8_000, runto=11_800
                ),
                _comparison_record(
                    "白銀のランス",
                    "shrink_wrapped",
                    collect=17_000,
                    runto=17_500,
                    inferred=True,
                ),
            ]
        ),
        previous_prices={"ステラミラクル": 11_000, "白銀のランス": 18_000},
    )
    requests = _comparison_format_requests(7, prepared)
    cols = list(prepared.columns)

    assert _text_ranges(requests, RED) == [_cell_range(7, (1, 2), cols.index("差率"))]
    assert _text_ranges(requests, UP_GREEN) == [_cell_range(7, (1, 2), cols.index("前回比"))]
    assert _text_ranges(requests, DOWN_BLUE) == [_cell_range(7, (2, 3), cols.index("前回比"))]
    assert _ranges_with_background(requests, YELLOW) == [
        _cell_range(7, (2, 3), cols.index("注意"))
    ]


def test_comparison_formatting_freezes_the_series_and_name_columns(
    comparison: pd.DataFrame,
) -> None:
    requests = _comparison_format_requests(7, _comparison_sheet_frame(comparison))

    frozen = [
        request["updateSheetProperties"]["properties"]["gridProperties"]
        for request in requests
        if "updateSheetProperties" in request
    ]
    assert frozen == [{"frozenRowCount": 1, "frozenColumnCount": 2}]
    assert any("setBasicFilter" in request for request in requests)
    assert requests[0] == {
        "repeatCell": {
            "range": {"sheetId": 7},
            "cell": {"userEnteredFormat": {}},
            "fields": "userEnteredFormat",
        }
    }


def test_history_row_reports_three_plus_and_single_site_rows_separately() -> None:
    comparison = pd.DataFrame({"matched_site_count": [5, 3, 2, 2, 1]})
    raw = pd.DataFrame({"source": ["homura", "tcgpro", "morimori", "runto", "somurie"]})

    assert _history_row(
        comparison,
        raw,
        fetched_at="2026-08-18T12:34:56+09:00",
        error_count=0,
    ) == ["2026-08-18 12:34", 5, 4, 2, 2, 0, 1]
    assert len(HISTORY_HEADERS) == 7


def test_prepare_history_rows_sorts_newest_first_and_backfills_legacy_rows() -> None:
    existing = [
        ["2026-08-17 09:00", "280", "147", "6", "66", "0"],
        ["2026-08-18 08:51", 280, 73, 5, 68, 0, 74],
    ]
    new_row = ["2026-08-18 17:00", 263, 78, 7, 71, 0, 62]

    prepared = _prepare_history_rows(existing, new_row, max_rows=2)

    assert prepared == [
        ["2026-08-18 17:00", 263, 78, 7, 71, 0, 62],
        ["2026-08-18 08:51", 280, 73, 5, 68, 0, 74],
    ]
    full = _prepare_history_rows(existing, new_row)
    assert full[-1] == ["2026-08-17 09:00", 280, 72, 6, 66, 0, 75]


def test_summary_counters_match_the_comparison_tab_row_count() -> None:
    labels = [row[0] for row in SUMMARY_COUNTER_ROWS]

    assert "BOX比較件数（2サイト以上）" in labels
    assert "1サイトのみ（単独掲載）" in labels
    assert "取得エラー" in labels
    single_listing = dict(SUMMARY_COUNTER_ROWS)["1サイトのみ（単独掲載）"]
    assert "更新履歴!G:G" in single_listing


def test_summary_write_stays_above_the_merged_link_row() -> None:
    """Row 9 is the merged link and rows 10+ are maintained by hand."""
    assert len(SUMMARY_COUNTER_ROWS) == SUMMARY_COUNTER_LIMIT
    assert SUMMARY_COUNTER_LIMIT == 6
    assert all(len(row) == 2 for row in SUMMARY_COUNTER_ROWS)


def test_summary_counters_read_the_newest_history_row_not_the_header() -> None:
    """LOOKUP(2,1/(...)) resolved to the header row and showed column names."""
    formulas = [row[1] for row in SUMMARY_COUNTER_ROWS]

    assert not any("LOOKUP(" in formula for formula in formulas)
    for formula in formulas[1:]:
        assert "MATCH(MAX(更新履歴!A2:A),更新履歴!A:A,0)" in formula


def test_ensure_summary_sheet_writes_all_sources_and_unmerges_legacy_rows() -> None:
    class FakeSummary:
        id = 10

        def __init__(self) -> None:
            self.a1 = None
            self.updates: list[tuple[str, list[list[object]]]] = []
            self.cleared_ranges: list[list[str]] = []

        def update_acell(self, cell: str, value: str) -> None:
            if cell == "A1":
                self.a1 = value

        def update(
            self,
            *,
            values: list[list[object]],
            range_name: str,
            value_input_option: str,
        ) -> None:
            self.updates.append((range_name, values))

        def batch_clear(self, ranges: list[str]) -> None:
            self.cleared_ranges.append(ranges)

    class FakeSpreadsheet:
        def __init__(self, summary: FakeSummary) -> None:
            self.summary = summary
            self.batches: list[dict[str, object]] = []

        def worksheet(self, _title: str) -> FakeSummary:
            return self.summary

        def batch_update(self, body: dict[str, object]) -> None:
            self.batches.append(body)

    summary = FakeSummary()
    spreadsheet = FakeSpreadsheet(summary)
    raw = pd.DataFrame({"source": ["homura", "homura", "tcgpro", "runto"]})
    _ensure_summary_sheet(spreadsheet, raw=raw)

    assert summary.a1 == SPREADSHEET_TITLE
    assert [rng for rng, _ in summary.updates] == ["A3", "A9", "C9", "A10"]
    assert "公開Web相場表" in str(summary.updates[2][1][0][0])
    source_block = summary.updates[3][1]
    assert source_block[1] == ["価格取得元", "状態", "今回件数", "シュリンク無", "公式価格表URL"]
    by_store = {row[0]: row for row in source_block[2:9]}
    assert by_store["買取ホムラ"][1:4] == ["稼働中", 2, "○"]
    assert by_store["トレカプロ"][1:4] == ["稼働中", 1, "×"]
    assert by_store["森森買取"][1:3] == ["未取得", 0]
    assert by_store["コレクト"][1:4] == ["一時中断", 0, "○"]
    assert summary.cleared_ranges == [["A22:F30"]]
    # First batch unmerges legacy merged rows below row 9 (e.g. old A14:F14).
    assert "unmergeCells" in spreadsheet.batches[0]["requests"][0]
    assert spreadsheet.batches[0]["requests"][0]["unmergeCells"]["range"]["startRowIndex"] == 9


def test_history_row_converts_cloud_utc_timestamp_to_japan_time() -> None:
    assert _history_row(
        pd.DataFrame(),
        pd.DataFrame(),
        fetched_at="2026-08-18T07:43:02+00:00",
        error_count=0,
    )[0] == "2026-08-18 16:43"


def _text_ranges(requests: list[dict], color: dict) -> list[dict]:
    return [
        request["repeatCell"]["range"]
        for request in requests
        if "repeatCell" in request
        and request["repeatCell"]["cell"]
        .get("userEnteredFormat", {})
        .get("textFormat", {})
        .get("foregroundColor")
        == color
    ]


def test_large_yen_gaps_are_marked_even_when_the_rate_is_small() -> None:
    """A 3.7% gap on an expensive box still pays more than a 32% gap on a cheap one."""
    frame = _comparison_sheet_frame(
        pd.DataFrame(
            [
                _comparison_record(
                    "イーブイヒーローズ", "shrink_wrapped", collect=130_000, runto=135_000
                ),
                _comparison_record("白熱のアルカナ", "no_shrink", collect=9_000, runto=10_500),
            ]
        )
    )

    assert list(frame["商品名"]) == ["イーブイヒーローズ"]
    requests = _comparison_format_requests(7, frame)
    cols = list(frame.columns)
    # The no-shrink row is excluded; the expensive shrink-wrapped box still marks its yen gap.
    assert _text_ranges(requests, RED) == []
    assert _text_ranges(requests, GOLD) == [_cell_range(7, (1, 2), cols.index("差額"))]


def test_header_notes_explain_the_narrow_columns(comparison: pd.DataFrame) -> None:
    prepared = _comparison_sheet_frame(comparison)
    cols = list(prepared.columns)
    requests = _comparison_format_requests(7, prepared)
    notes = {
        request["updateCells"]["range"]["startColumnIndex"]: request["updateCells"]["rows"][0][
            "values"
        ][0]["note"]
        for request in requests
        if "updateCells" in request
    }

    expected_indices = {cols.index(name) for name in COMPARISON_HEADER_NOTES_BY_NAME}
    assert set(notes) == expected_indices
    assert "前回比" in notes[cols.index("前回比")]
    assert "定価比" in notes[cols.index("定価比")]
    assert "状態推定" in notes[cols.index("注意")]
    assert all(
        request["updateCells"]["range"]["startRowIndex"] == 0
        for request in requests
        if "updateCells" in request
    )


def test_history_backfill_restates_rows_written_before_the_new_column() -> None:
    rows = [
        # Old layout: C counted every comparison row, G did not exist yet.
        ["2026-08-17 09:00", 280, 147, 6, 66, 0],
        ["2026-08-18 08:51", 280, 147, 6, 66, 0],
        # Already migrated, so it must be left alone.
        ["2026-08-18 21:25", 280, 73, 5, 68, 0, 74],
    ]

    assert _history_backfill_updates(rows) == [
        {"range": "C2", "values": [[72]]},
        {"range": "G2", "values": [[75]]},
        {"range": "C3", "values": [[72]]},
        {"range": "G3", "values": [[75]]},
    ]


def test_history_backfill_skips_rows_it_cannot_restate() -> None:
    rows = [
        [],
        ["", "", "", "", "", ""],
        ["2026-08-18 08:51", 280, "-", 6, 66, 0],
        # A row whose counts cannot add up is left for a human to look at.
        ["2026-08-18 08:52", 280, 70, 6, 66, 0],
    ]

    assert _history_backfill_updates(rows) == []
