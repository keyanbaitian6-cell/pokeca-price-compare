import pandas as pd
import pytest

from card_price_compare.collectors.collect_sheet import SPREADSHEET_ID
from card_price_compare.google_output import (
    COMPARISON_COLUMNS,
    COMPARISON_HEADER_NOTES,
    HISTORY_HEADERS,
    MANUAL_UPDATE_FORMULA,
    MANUAL_UPDATE_URL,
    SINGLE_LISTING_COLUMNS,
    SUMMARY_COUNTER_LIMIT,
    SUMMARY_COUNTER_ROWS,
    _comparison_format_requests,
    _comparison_sheet_frame,
    _history_backfill_updates,
    _history_row,
    _raw_sheet_frame,
    _row_runs,
    _single_listing_sheet_frame,
    _store_label,
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


def test_comparison_tab_keeps_ten_readable_columns(comparison: pd.DataFrame) -> None:
    prepared = _comparison_sheet_frame(comparison)

    assert list(prepared.columns) == COMPARISON_COLUMNS
    assert len(prepared) == 3
    # The original store names stay on the raw tab instead of widening this one.
    assert "runto商品名" not in prepared.columns


def test_comparison_tab_is_sorted_by_spread_rate(comparison: pd.DataFrame) -> None:
    prepared = _comparison_sheet_frame(comparison)

    assert list(prepared["商品名"]) == ["ステラミラクル", "白銀のランス", "ストームエメラルダ"]
    assert prepared.iloc[0]["差額"] == 3_800
    assert prepared.iloc[0]["差率"] == pytest.approx(3_800 / 11_800)
    assert prepared.iloc[2]["差率"] == 0.0


def test_comparison_tab_names_the_best_store_in_japanese(comparison: pd.DataFrame) -> None:
    prepared = _comparison_sheet_frame(comparison)

    assert prepared.iloc[0]["最高値の店"] == "runto"
    assert prepared.iloc[0]["最高値"] == 11_800
    assert prepared.iloc[2]["最高値の店"] == "3店同額"


def test_tied_best_stores_are_joined_with_a_middle_dot() -> None:
    assert _store_label("collect") == "コレクト"
    assert _store_label("collect,runto") == "コレクト・runto"
    assert _store_label("collect,somurie") == "コレクト・買取ソムリエ"
    assert _store_label("collect,runto,somurie") == "3店同額"
    assert _store_label("") == ""


def test_inferred_condition_is_flagged_in_the_warning_column(comparison: pd.DataFrame) -> None:
    prepared = _comparison_sheet_frame(comparison)

    assert prepared.iloc[1]["商品名"] == "白銀のランス"
    assert prepared.iloc[1]["注意"] == "状態推定"
    assert prepared.iloc[0]["注意"] == ""


def test_single_listing_tab_lists_one_store_rows_by_price(comparison: pd.DataFrame) -> None:
    prepared = _single_listing_sheet_frame(comparison)

    assert list(prepared.columns) == SINGLE_LISTING_COLUMNS
    assert list(prepared["商品名"]) == ["第1弾", "e 基本 海からの風"]
    assert list(prepared["掲載店"]) == ["runto", "コレクト"]
    assert prepared.iloc[0]["買取価格"] == 13_000_000
    assert prepared.iloc[0]["状態"] == "状態不明"


def test_empty_comparison_still_produces_both_tab_layouts() -> None:
    empty = pd.DataFrame()

    assert list(_comparison_sheet_frame(empty).columns) == COMPARISON_COLUMNS
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

    # runto wins rows 1 and 2; row 3 is a three-way tie, so all three go green.
    assert _ranges_with_background(requests, GREEN) == [
        _cell_range(123, (3, 4), 6),
        _cell_range(123, (1, 4), 7),
        _cell_range(123, (3, 4), 8),
    ]


def test_comparison_formatting_marks_high_spread_rates_and_warnings(
    comparison: pd.DataFrame,
) -> None:
    prepared = _comparison_sheet_frame(comparison)
    requests = _comparison_format_requests(7, prepared)

    red_ranges = [
        request["repeatCell"]["range"]
        for request in requests
        if "repeatCell" in request
        and request["repeatCell"]["cell"]
        .get("userEnteredFormat", {})
        .get("textFormat", {})
        .get("foregroundColor")
        == RED
    ]
    # Only ステラミラクル clears the 5% threshold.
    assert red_ranges == [_cell_range(7, (1, 2), 4)]
    assert _ranges_with_background(requests, YELLOW) == [_cell_range(7, (2, 3), 9)]


def test_comparison_formatting_freezes_the_name_and_condition_columns(
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


def test_history_row_reports_single_site_rows_separately() -> None:
    comparison = pd.DataFrame({"matched_site_count": [3, 2, 2, 1]})
    raw = pd.DataFrame({"source": ["collect", "runto", "somurie"]})

    assert _history_row(
        comparison,
        raw,
        fetched_at="2026-08-18T12:34:56+09:00",
        error_count=0,
    ) == ["2026-08-18 12:34", 3, 3, 1, 2, 0, 1]
    assert len(HISTORY_HEADERS) == 7


def test_summary_counters_match_the_comparison_tab_row_count() -> None:
    labels = [row[0] for row in SUMMARY_COUNTER_ROWS]

    assert "BOX比較件数（2サイト以上）" in labels
    assert "1サイトのみ（単独掲載）" in labels
    assert "取得エラー" in labels
    single_listing = dict(SUMMARY_COUNTER_ROWS)["1サイトのみ（単独掲載）"]
    assert "更新履歴!G:G" in single_listing


def test_summary_write_stays_above_the_merged_link_row() -> None:
    """Row 9 is the merged link and rows 10+ are maintained by hand."""
    # A3 plus six rows ends at row 8, so nothing reaches row 9 or below.
    assert len(SUMMARY_COUNTER_ROWS) == SUMMARY_COUNTER_LIMIT
    assert SUMMARY_COUNTER_LIMIT == 6
    assert all(len(row) == 2 for row in SUMMARY_COUNTER_ROWS)


def test_summary_counters_read_the_newest_history_row_not_the_header() -> None:
    """LOOKUP(2,1/(...)) resolved to the header row and showed column names."""
    formulas = [row[1] for row in SUMMARY_COUNTER_ROWS]

    assert not any("LOOKUP(" in formula for formula in formulas)
    for formula in formulas[1:]:
        assert "MATCH(MAX(更新履歴!A2:A),更新履歴!A:A,0)" in formula


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
                _comparison_record("イーブイヒーローズ", "shrink_wrapped", collect=130_000, runto=135_000),
                _comparison_record("白熱のアルカナ", "no_shrink", collect=9_000, runto=10_500),
            ]
        )
    )

    assert list(frame["商品名"]) == ["白熱のアルカナ", "イーブイヒーローズ"]
    requests = _comparison_format_requests(7, frame)
    # 白熱のアルカナ clears 5% but not 3,000 yen; イーブイヒーローズ is the reverse.
    assert _text_ranges(requests, RED) == [_cell_range(7, (1, 2), 4)]
    assert _text_ranges(requests, GOLD) == [_cell_range(7, (2, 3), 5)]


def test_header_notes_explain_the_narrow_columns(comparison: pd.DataFrame) -> None:
    requests = _comparison_format_requests(7, _comparison_sheet_frame(comparison))
    notes = {
        request["updateCells"]["range"]["startColumnIndex"]: request["updateCells"]["rows"][0][
            "values"
        ][0]["note"]
        for request in requests
        if "updateCells" in request
    }

    assert set(notes) == set(COMPARISON_HEADER_NOTES)
    assert "状態推定" in notes[9]
    assert all(request["updateCells"]["range"]["startRowIndex"] == 0 for request in requests if "updateCells" in request)


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
