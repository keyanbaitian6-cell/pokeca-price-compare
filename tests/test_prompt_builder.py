from __future__ import annotations

import json

import pandas as pd

from card_price_compare.market_analysis import analyze_market
from card_price_compare.prompt_builder import (
    PROMPT_SHEET_HEADERS,
    TOOL_SITE_BASE_URL,
    build_prompt_bundle,
    find_leaked_store_terms,
    main as prompt_builder_main,
    write_prompt_outputs,
)


def _sample_insights():
    comparison = pd.DataFrame(
        [
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
            },
            {
                "product_name_normalized": "イーブイヒーローズ",
                "condition": "shrink_wrapped",
                "condition_inferred": False,
                "collect_price_yen": pd.NA,
                "runto_price_yen": 135_000,
                "somurie_price_yen": 130_000,
                "best_site": "runto",
                "best_price_yen": 135_000,
                "spread_yen": 5_000,
                "matched_site_count": 2,
            },
        ]
    )
    trend = pd.DataFrame(
        [
            ["2026-11-17", "テラスタルフェスex", 10_000, "runto"],
            ["2026-11-23", "テラスタルフェスex", 12_000, "runto"],
            ["2026-11-24", "テラスタルフェスex", 14_400, "買取ソムリエ"],
            ["2026-11-17", "151", 20_000, "runto"],
            ["2026-11-23", "151", 22_000, "runto"],
            ["2026-11-24", "151", 23_100, "買取ソムリエ"],
            ["2026-11-17", "ステラミラクル", 13_000, "runto"],
            ["2026-11-23", "ステラミラクル", 12_500, "runto"],
            ["2026-11-24", "ステラミラクル", 11_800, "runto"],
        ],
        columns=["日付", "商品名", "最高値", "最高値の店"],
    )
    return analyze_market(comparison, trend, fetched_at="2026-11-24T17:00:00+09:00")


def test_prompt_bundle_contains_all_required_x_and_note_prompts_and_tool_links() -> None:
    insights = _sample_insights()
    bundle = build_prompt_bundle(insights)

    entry_ids = [entry.entry_id for entry in bundle.entries]
    assert entry_ids == [
        "market_digest",
        "x_breaking",
        "x_insight",
        "x_tool_funnel",
        "weekly_note",
        "quick_x_drafts",
        "funnel_templates",
    ]

    # X breaking prompt includes movers, 7-day data, sentiment, and portfolio tool link
    breaking = bundle.get_entry("x_breaking").prompt_text
    assert "テラスタルフェスex" in breaking
    assert "ステラミラクル" in breaking
    assert "+2,400円" in breaking
    assert "2026年11月24日" in breaking
    assert f"{TOOL_SITE_BASE_URL}portfolio.html" in breaking

    # X insight prompt includes both high-rate and high-yen spreads + sell-compare link + #PR rule
    insight = bundle.get_entry("x_insight").prompt_text
    assert "ステラミラクル" in insight
    assert "イーブイヒーローズ" in insight
    assert "32.2%" in insight
    assert "5,000円" in insight
    assert f"{TOOL_SITE_BASE_URL}sell-compare.html" in insight
    assert "#PR" in insight

    # X tool funnel prompt embeds exact break-even math & トレカ損益ラボ URLs
    funnel = bundle.get_entry("x_tool_funnel").prompt_text
    assert "トレカ損益ラボ" in funnel
    assert TOOL_SITE_BASE_URL in funnel
    assert f"{TOOL_SITE_BASE_URL}sell-compare.html" in funnel
    assert f"{TOOL_SITE_BASE_URL}portfolio.html" in funnel
    assert f"{TOOL_SITE_BASE_URL}psa.html" in funnel
    assert f"{TOOL_SITE_BASE_URL}oripa.html" in funnel
    # Representative box is ステラミラクル (11,800 yen) -> Mercari break-even = 13,822 yen
    assert "11,800円" in funnel
    assert "13,822円" in funnel

    # Weekly note prompt includes free intro + paid paywall structure + 7d movers + tool links
    note = bundle.get_entry("weekly_note").prompt_text
    assert "無料パート" in note
    assert "有料パート" in note
    assert "メンバーシップ" in note
    assert "7日前比 急上昇BOX" in note
    assert "テラスタルフェスex" in note
    assert "+44.0%" in note
    assert f"{TOOL_SITE_BASE_URL}sell-compare.html" in note


def test_prompts_and_drafts_never_leak_store_names_or_recommend_rakuten_room() -> None:
    insights = _sample_insights()
    bundle = build_prompt_bundle(insights)

    all_text = "\n".join(
        [bundle.to_markdown(), json.dumps(bundle.to_dict(), ensure_ascii=False)]
    )
    assert find_leaked_store_terms(all_text) == []
    assert "楽天ROOM" not in all_text
    assert "楽天room" not in all_text.casefold()
    assert "OpenAI" not in all_text
    assert "APIキー" not in bundle.get_entry("x_breaking").prompt_text


def test_prompt_bundle_handles_empty_data_without_errors() -> None:
    empty_insights = analyze_market(
        pd.DataFrame(), pd.DataFrame(), fetched_at="2026-11-24T17:00:00+09:00"
    )
    bundle = build_prompt_bundle(empty_insights)

    rows = bundle.to_sheet_rows()
    assert rows[0] == PROMPT_SHEET_HEADERS
    assert len(rows) == len(bundle.entries) + 1
    assert all(len(row) == len(PROMPT_SHEET_HEADERS) for row in rows)
    # Every cell must stay far below Google Sheets' 50,000-char cell limit
    assert all(len(str(cell)) < 15_000 for row in rows for cell in row)
    assert find_leaked_store_terms(bundle.to_markdown()) == []
    # Fallback example still provides valid break-even numbers
    assert "12,000円" in bundle.get_entry("x_tool_funnel").prompt_text


def test_write_prompt_outputs_and_standalone_cli(tmp_path) -> None:
    insights = _sample_insights()
    bundle = build_prompt_bundle(insights)
    paths = write_prompt_outputs(insights, bundle, tmp_path)

    assert paths["market_insights"].exists()
    assert paths["ai_prompts_json"].exists()
    assert paths["ai_prompts_md"].exists()

    loaded_insights = json.loads(paths["market_insights"].read_text(encoding="utf-8"))
    assert loaded_insights["as_of_date"] == "2026-11-24"
    loaded_prompts = json.loads(paths["ai_prompts_json"].read_text(encoding="utf-8"))
    assert len(loaded_prompts["entries"]) == 7
    md_text = paths["ai_prompts_md"].read_text(encoding="utf-8")
    assert "# ポケカ未開封BOX 発信プロンプト＆下書き素材" in md_text
    assert find_leaked_store_terms(md_text) == []

    # Verify standalone CLI can regenerate from CSVs with zero network access
    comp_csv = tmp_path / "box_comparison.csv"
    trend_csv = tmp_path / "shrink_trend_history.csv"
    pd.DataFrame(
        [
            {
                "product_name_normalized": "151",
                "condition": "shrink_wrapped",
                "condition_inferred": False,
                "best_price_yen": 25_000,
                "spread_yen": 2_000,
                "matched_site_count": 2,
            }
        ]
    ).to_csv(comp_csv, index=False, encoding="utf-8-sig")
    pd.DataFrame(
        [
            ["2026-11-17", "151", 21_000, "runto"],
            ["2026-11-24", "151", 25_000, "買取ソムリエ"],
        ],
        columns=["日付", "商品名", "最高値", "最高値の店"],
    ).to_csv(trend_csv, index=False, encoding="utf-8-sig")

    out_dir = tmp_path / "regenerated"
    rc = prompt_builder_main(
        [
            "--comparison-csv",
            str(comp_csv),
            "--trend-csv",
            str(trend_csv),
            "--output-dir",
            str(out_dir),
        ]
    )
    assert rc == 0
    regenerated_md = (out_dir / "ai_prompts.md").read_text(encoding="utf-8")
    assert "151" in regenerated_md
    assert "+4,000円" in regenerated_md
    assert find_leaked_store_terms(regenerated_md) == []
