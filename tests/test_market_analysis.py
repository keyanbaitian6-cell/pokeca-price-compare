from __future__ import annotations

import json

import pandas as pd
import pytest

from card_price_compare.market_analysis import (
    analyze_market,
    solve_break_even_selling_price,
)
from card_price_compare.prompt_builder import find_leaked_store_terms


def _comparison_row(
    name: str,
    condition: str,
    *,
    collect: int | None = None,
    runto: int | None = None,
    somurie: int | None = None,
    inferred: bool = False,
) -> dict[str, object]:
    prices = {"collect": collect, "runto": runto, "somurie": somurie}
    present = {src: val for src, val in prices.items() if val is not None}
    best_price = max(present.values())
    best_site = ",".join(src for src, val in present.items() if val == best_price)
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


def test_solve_break_even_selling_price_matches_site_calculator() -> None:
    # Unopened BOX preset on トレカ損益ラボ: shipping 520 + packing 120 = 640
    # Target net = 10,500 on Mercari (10% fee, floored):
    # P = 12,378 -> floor(1237.8) = 1237 -> 12378 - 1237 - 640 = 10,501 >= 10,500
    # P = 12,377 -> floor(1237.7) = 1237 -> 12377 - 1237 - 640 = 10,500 >= 10,500!
    assert solve_break_even_selling_price(10_500, 0.10, 640) == 12_377
    assert solve_break_even_selling_price(18_000, 0.10, 640) == 20_711
    # Verify exact invariant P - floor(P * r) - fixed >= target and (P-1) fails
    for target in (5_000, 10_500, 18_000, 135_000):
        for rate in (0.05, 0.07, 0.085, 0.10):
            p = solve_break_even_selling_price(target, rate, 640)
            assert p - int(p * rate) - 640 >= target
            assert (p - 1) - int((p - 1) * rate) - 640 < target
    assert solve_break_even_selling_price(0, 0.10, 0) == 0


def test_analyze_market_ranks_prev_and_7d_movers_and_sentiment() -> None:
    trend = pd.DataFrame(
        [
            # 151: steady rise (+10% prev, +20% 7d)
            ["2026-11-16", "151", "¥20,000", "runto"],
            ["2026-11-23", "151", 22_000, "runto"],
            ["2026-11-24", "151", 24_200, "買取ソムリエ"],
            # テラスタルフェスex: sharp prev surge (+25% prev, +50% 7d)
            ["2026-11-17", "テラスタルフェスex SV8a", 10_000, "runto"],
            ["2026-11-23", "テラスタルフェスex", 12_000, "runto"],
            ["2026-11-24", "テラスタルフェスex", 15_000, "買取ソムリエ"],
            # クレイバースト: small rise (+5% prev, +5% 7d)
            ["2026-11-17", "クレイバースト", 10_000, "runto"],
            ["2026-11-23", "クレイバースト", 10_000, "runto"],
            ["2026-11-24", "クレイバースト", 10_500, "runto"],
            # ステラミラクル: drop (-10% prev, -20% 7d)
            ["2026-11-17", "ステラミラクル", 10_000, "runto"],
            ["2026-11-23", "ステラミラクル", 9_000, "runto"],
            ["2026-11-24", "ステラミラクル", 8_100, "runto"],
            # 楽園ドラゴーナ: flat
            ["2026-11-17", "楽園ドラゴーナ", 8_000, "runto"],
            ["2026-11-23", "楽園ドラゴーナ", 8_000, "runto"],
            ["2026-11-24", "楽園ドラゴーナ", 8_000, "runto"],
            # Stale box (not observed on latest day 2026-11-24): must be excluded
            ["2026-11-17", "絶版テストBOX", 50_000, "runto"],
            ["2026-11-20", "絶版テストBOX", 60_000, "runto"],
        ],
        columns=["日付", "商品名", "最高値", "最高値の店"],
    )

    insights = analyze_market(
        pd.DataFrame(),
        trend,
        fetched_at="2026-11-24T17:00:00+09:00",
        top_n=3,
    )

    assert insights.as_of_date == "2026-11-24"
    assert insights.tracked_box_count == 5
    assert insights.history_days_available == 5

    # Sentiment: 3 up, 1 down, 1 flat -> 強気（上昇優勢）
    assert insights.sentiment.compared_prev_count == 5
    assert insights.sentiment.prev_up_count == 3
    assert insights.sentiment.prev_down_count == 1
    assert insights.sentiment.prev_flat_count == 1
    assert insights.sentiment.compared_7d_count == 5
    assert insights.sentiment.week_up_count == 3
    assert insights.sentiment.week_down_count == 1
    assert insights.sentiment.week_flat_count == 1
    assert insights.sentiment.mood_label == "強気（上昇優勢）"

    # Prev gainers ranked by diff_rate desc
    assert [m.product_name for m in insights.prev_gainers] == [
        "テラスタルフェスex",
        "151",
        "クレイバースト",
    ]
    assert insights.prev_gainers[0].diff_yen == 3_000
    assert insights.prev_gainers[0].diff_rate == pytest.approx(0.25)

    # Prev losers
    assert [m.product_name for m in insights.prev_losers] == ["ステラミラクル"]
    assert insights.prev_losers[0].diff_yen == -900
    assert insights.prev_losers[0].diff_rate == pytest.approx(-0.1)

    # 7d gainers: 151 uses 2026-11-16 (8 days prior since 2026-11-17 missing)
    assert [m.product_name for m in insights.week_gainers] == [
        "テラスタルフェスex",
        "151",
        "クレイバースト",
    ]
    assert insights.week_gainers[1].reference_date == "2026-11-16"
    assert insights.week_gainers[1].diff_yen == 4_200
    assert insights.week_gainers[1].diff_rate == pytest.approx(0.21)

    # 7d losers
    assert [m.product_name for m in insights.week_losers] == ["ステラミラクル"]
    assert insights.week_losers[0].diff_yen == -1_900

    # Store names must never leak into MarketInsights serialized output
    serialized = json.dumps(insights.to_dict(), ensure_ascii=False)
    assert find_leaked_store_terms(serialized) == []


def test_analyze_market_captures_both_high_rate_and_high_yen_spreads_without_store_names() -> None:
    comparison = pd.DataFrame(
        [
            # High spread rate (32.2%), moderate yen (3,800)
            _comparison_row("ステラミラクル", "shrink_wrapped", runto=11_800, somurie=8_000),
            # Low spread rate (3.7%), highest yen gap (5,000) — DECISIONS.md Eevee Heroes case!
            _comparison_row("イーブイヒーローズ", "shrink_wrapped", runto=135_000, somurie=130_000),
            # Zero spread — excluded from spread rankings
            _comparison_row("ストームエメラルダ", "shrink_wrapped", runto=18_000, somurie=18_000),
            # Inferred condition — excluded by default
            _comparison_row(
                "白銀のランス", "shrink_wrapped", runto=17_500, somurie=15_000, inferred=True
            ),
            # No-shrink & single-store — excluded
            _comparison_row("超電ブレイカー", "no_shrink", runto=10_000, somurie=7_000),
            _comparison_row("第1弾", "unspecified", runto=13_000_000),
        ]
    )

    insights = analyze_market(comparison, pd.DataFrame(), fetched_at="2026-11-24T17:00:00+09:00")

    assert insights.multi_store_box_count == 4  # 4 shrink_wrapped rows with >=2 sites
    assert insights.inferred_spread_excluded_count == 1
    assert insights.high_spread_box_count == 2  # ステラミラクル (>=5%) + イーブイヒーローズ (>=3000円)

    assert [s.product_name for s in insights.spread_by_rate] == [
        "ステラミラクル",
        "イーブイヒーローズ",
    ]
    assert [s.product_name for s in insights.spread_by_yen] == [
        "イーブイヒーローズ",
        "ステラミラクル",
    ]
    assert insights.spread_by_yen[0].highlight_reason == "差額3,000円以上"
    assert insights.spread_by_rate[0].highlight_reason == "差率5%以上＆差額3,000円以上"
    assert insights.spread_by_rate[0].lowest_price_yen == 8_000
    assert insights.spread_by_rate[0].best_price_yen == 11_800

    # Combined highlights preserve both perspectives
    combined_names = [s.product_name for s in insights.combined_spread_highlights]
    assert "ステラミラクル" in combined_names
    assert "イーブイヒーローズ" in combined_names
    assert "白銀のランス" not in combined_names

    serialized = json.dumps(insights.to_dict(), ensure_ascii=False)
    assert find_leaked_store_terms(serialized) == []


def test_analyze_market_handles_first_day_and_empty_inputs_gracefully() -> None:
    empty_insights = analyze_market(
        pd.DataFrame(), pd.DataFrame(), fetched_at="2026-11-24T17:00:00+09:00"
    )
    assert empty_insights.tracked_box_count == 0
    assert empty_insights.prev_gainers == []
    assert empty_insights.week_gainers == []
    assert empty_insights.combined_spread_highlights == []
    assert "履歴蓄積中" in empty_insights.sentiment.mood_label

    day1_trend = pd.DataFrame(
        [["2026-11-24", "151", 25_000, "runto"]],
        columns=["日付", "商品名", "最高値", "最高値の店"],
    )
    day1 = analyze_market(pd.DataFrame(), day1_trend, fetched_at="2026-11-24T17:00:00+09:00")
    assert day1.tracked_box_count == 1
    assert day1.history_days_available == 1
    assert day1.sentiment.compared_prev_count == 0
    assert "履歴蓄積中" in day1.sentiment.mood_label


def test_analyze_market_classifies_bearish_and_flat_sentiments() -> None:
    bearish_trend = pd.DataFrame(
        [
            ["2026-11-23", "BOX_A", 10_000, "runto"],
            ["2026-11-24", "BOX_A", 9_000, "runto"],
            ["2026-11-23", "BOX_B", 10_000, "runto"],
            ["2026-11-24", "BOX_B", 9_200, "runto"],
            ["2026-11-23", "BOX_C", 10_000, "runto"],
            ["2026-11-24", "BOX_C", 9_500, "runto"],
        ],
        columns=["日付", "商品名", "最高値", "最高値の店"],
    )
    bearish = analyze_market(pd.DataFrame(), bearish_trend, fetched_at="2026-11-24T17:00:00+09:00")
    assert bearish.sentiment.mood_label == "弱気（下落優勢）"

    flat_trend = pd.DataFrame(
        [
            ["2026-11-23", "BOX_A", 10_000, "runto"],
            ["2026-11-24", "BOX_A", 10_000, "runto"],
        ],
        columns=["日付", "商品名", "最高値", "最高値の店"],
    )
    flat = analyze_market(pd.DataFrame(), flat_trend, fetched_at="2026-11-24T17:00:00+09:00")
    assert flat.sentiment.mood_label == "横ばい・膠着"
