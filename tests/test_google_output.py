import pandas as pd
import pytest

from card_price_compare.collectors.collect_sheet import SPREADSHEET_ID
from card_price_compare.google_output import (
    _comparison_sheet_frame,
    _history_row,
    _raw_sheet_frame,
    publish_frames,
)


def test_collect_source_sheet_cannot_be_output_target(tmp_path) -> None:
    with pytest.raises(ValueError, match="参照元"):
        publish_frames(
            spreadsheet_id=SPREADSHEET_ID,
            credentials_file=tmp_path / "not-used.json",
            comparison=pd.DataFrame(),
            raw=pd.DataFrame(),
        )


def test_comparison_google_headers_include_clear_unknown_condition_warning() -> None:
    prepared = _comparison_sheet_frame(
        pd.DataFrame(
            [
                {
                    "product_name_normalized": "白銀のランス",
                    "condition": "shrink_wrapped",
                    "condition_inferred": True,
                }
            ]
        )
    )
    assert list(prepared.columns) == ["商品名（名寄せ後）", "状態", "状態の注意"]
    assert prepared.iloc[0]["状態"] == "シュリンク有"
    assert prepared.iloc[0]["状態の注意"] == "一部店舗で状態不明"


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


def test_history_row_contains_manual_run_summary() -> None:
    comparison = pd.DataFrame({"matched_site_count": [3, 2, 2, 1]})
    raw = pd.DataFrame({"source": ["collect", "runto", "somurie"]})

    assert _history_row(
        comparison,
        raw,
        fetched_at="2026-08-18T12:34:56+09:00",
        error_count=0,
    ) == ["2026-08-18 12:34", 3, 4, 1, 2, 0]


def test_history_row_converts_cloud_utc_timestamp_to_japan_time() -> None:
    assert _history_row(
        pd.DataFrame(),
        pd.DataFrame(),
        fetched_at="2026-08-18T07:43:02+00:00",
        error_count=0,
    )[0] == "2026-08-18 16:43"
