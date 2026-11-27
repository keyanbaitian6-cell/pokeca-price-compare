from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .catalog import SERIES_SORT_ORDER, lookup_box_metadata
from .market_analysis import MarketInsights, analyze_market, solve_break_even_selling_price
from .normalize import normalize_product_name
from .prompt_builder import (
    DEFAULT_BOX_MERCARI_FEE_RATE,
    DEFAULT_BOX_PACKING_YEN,
    DEFAULT_BOX_SHIPPING_YEN,
    DEFAULT_BOX_YAHOO_FEE_RATE,
    find_leaked_store_terms,
)


JAPAN_TIME_ZONE = timezone(timedelta(hours=9), name="JST")
SPARKLINE_MAX_POINTS = 30


def _optional_int(value: object) -> int | None:
    if value is None or value is pd.NA:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _build_trend_series_map(
    trend_history: pd.DataFrame | None,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, int], dict[str, int]]:
    """Build per-box anonymized 30-day sparkline series and prior / 7d price deltas."""
    if trend_history is None or trend_history.empty:
        return {}, {}, {}
    required = {"日付", "商品名", "最高値"}
    if not required.issubset(trend_history.columns):
        return {}, {}, {}

    df = trend_history[["日付", "商品名", "最高値"]].copy()
    df["日付"] = df["日付"].astype(str).str.strip()
    df["商品名"] = df["商品名"].astype(str).map(normalize_product_name)
    df["最高値"] = pd.to_numeric(
        df["最高値"].astype(str).str.replace(r"[^0-9.-]", "", regex=True),
        errors="coerce",
    )
    df = df[(df["日付"] != "") & (df["商品名"] != "") & df["最高値"].notna()].copy()
    if df.empty:
        return {}, {}, {}
    df["最高値"] = df["最高値"].astype(int)
    df = df[df["最高値"] > 0]
    df = df.sort_values(["日付", "商品名", "最高値"], ascending=[True, True, False], kind="mergesort")
    df = df.drop_duplicates(["日付", "商品名"], keep="first")

    series_map: dict[str, list[dict[str, Any]]] = {}
    prev_diff_map: dict[str, int] = {}
    week_diff_map: dict[str, int] = {}

    for name, group in df.groupby("商品名", sort=False):
        ordered = group.sort_values("日付", kind="mergesort")
        points = [
            {"date": str(d), "price": int(p)}
            for d, p in zip(ordered["日付"], ordered["最高値"])
        ]
        if not points:
            continue
        series_map[str(name)] = points[-SPARKLINE_MAX_POINTS:]
        if len(points) >= 2:
            prev_diff_map[str(name)] = points[-1]["price"] - points[-2]["price"]
        try:
            latest_date = datetime.fromisoformat(points[-1]["date"]).date()
            cutoff = (latest_date - timedelta(days=7)).isoformat()
            older = [pt["price"] for pt in points if pt["date"] <= cutoff]
            if older:
                week_diff_map[str(name)] = points[-1]["price"] - older[-1]
        except ValueError:
            pass

    return series_map, prev_diff_map, week_diff_map


def build_web_market_payload(
    comparison: pd.DataFrame,
    trend_history: pd.DataFrame | None = None,
    *,
    fetched_at: str | None = None,
    active_store_count: int | None = None,
    insights: MarketInsights | None = None,
) -> dict[str, Any]:
    """Build a strictly store-anonymized JSON payload for the public web price index.

    Individual shop names, shop URLs, and raw store-by-store price tables are never
    emitted; only aggregated market ranges, medians, spread rates, MSRP multipliers,
    and historical trend points are published.
    """
    effective_fetched_at = fetched_at or datetime.now(JAPAN_TIME_ZONE).isoformat(timespec="seconds")
    resolved_insights = insights or analyze_market(
        comparison,
        trend_history,
        fetched_at=effective_fetched_at,
    )
    series_map, prev_diff_map, week_diff_map = _build_trend_series_map(trend_history)

    # Index no-shrink market highs/lows by normalized product name.
    no_shrink_map: dict[str, dict[str, int]] = {}
    if comparison is not None and not comparison.empty and "condition" in comparison.columns:
        ns_df = comparison[
            (comparison["condition"] == "no_shrink") & comparison["best_price_yen"].notna()
        ]
        for _, row in ns_df.iterrows():
            key = normalize_product_name(str(row["product_name_normalized"]))
            best = _optional_int(row.get("best_price_yen"))
            if not key or best is None or best <= 0:
                continue
            low = _optional_int(row.get("lowest_price_yen"))
            if low is None:
                spread = _optional_int(row.get("spread_yen")) or 0
                low = max(0, best - spread)
            count = _optional_int(row.get("matched_site_count")) or 1
            no_shrink_map[key] = {
                "high": best,
                "low": low,
                "store_count": count,
            }

    items: list[dict[str, Any]] = []
    if comparison is not None and not comparison.empty and "condition" in comparison.columns:
        shrink_df = comparison[
            (comparison["condition"] == "shrink_wrapped") & comparison["best_price_yen"].notna()
        ].copy()
        for _, row in shrink_df.iterrows():
            key = normalize_product_name(str(row["product_name_normalized"]))
            high = _optional_int(row.get("best_price_yen"))
            if not key or high is None or high <= 0:
                continue
            store_count = _optional_int(row.get("matched_site_count")) or 1
            spread_yen = _optional_int(row.get("spread_yen"))
            if spread_yen is None:
                spread_yen = 0
            low = _optional_int(row.get("lowest_price_yen"))
            if low is None:
                low = max(0, high - spread_yen)
            median_price = _optional_int(row.get("median_price_yen"))
            if median_price is None:
                median_price = int(round((high + low) / 2))
            second_best = _optional_int(row.get("second_best_price_yen"))
            top_lead = _optional_int(row.get("top_lead_yen"))
            inferred = bool(row.get("condition_inferred", False))

            spread_rate = round(spread_yen / high, 4) if store_count >= 2 and high > 0 else 0.0
            meta = lookup_box_metadata(key)
            msrp = meta.msrp_yen
            msrp_ratio = round(high / msrp, 2) if msrp and msrp > 0 else None
            msrp_diff = high - msrp if msrp and msrp > 0 else None

            ns_info = no_shrink_map.get(key)
            no_shrink_high = ns_info["high"] if ns_info else None
            shrink_gap_yen = (high - no_shrink_high) if no_shrink_high is not None else None
            shrink_gap_rate = (
                round(shrink_gap_yen / high, 4)
                if shrink_gap_yen is not None and high > 0
                else None
            )

            mercari_break_even = solve_break_even_selling_price(
                high,
                DEFAULT_BOX_MERCARI_FEE_RATE,
                DEFAULT_BOX_SHIPPING_YEN + DEFAULT_BOX_PACKING_YEN,
            )
            yahoo_break_even = solve_break_even_selling_price(
                high,
                DEFAULT_BOX_YAHOO_FEE_RATE,
                DEFAULT_BOX_SHIPPING_YEN + DEFAULT_BOX_PACKING_YEN,
            )

            points = series_map.get(key, [])
            prev_diff = prev_diff_map.get(key)
            week_diff = week_diff_map.get(key)

            items.append(
                {
                    "id": key,
                    "name": meta.display_name,
                    "series": meta.series,
                    "set_code": meta.set_code,
                    "release_date": meta.release_date,
                    "msrp_yen": msrp,
                    "msrp_ratio": msrp_ratio,
                    "msrp_diff_yen": msrp_diff,
                    "high_yen": high,
                    "median_yen": median_price,
                    "low_yen": low,
                    "second_best_yen": second_best,
                    "top_lead_yen": top_lead,
                    "spread_yen": spread_yen if store_count >= 2 else 0,
                    "spread_rate": spread_rate,
                    "store_count": store_count,
                    "condition_inferred": inferred,
                    "no_shrink_high_yen": no_shrink_high,
                    "no_shrink_gap_yen": shrink_gap_yen,
                    "no_shrink_gap_rate": shrink_gap_rate,
                    "prev_diff_yen": prev_diff,
                    "week_diff_yen": week_diff,
                    "mercari_break_even_yen": mercari_break_even,
                    "yahoo_break_even_yen": yahoo_break_even,
                    "trend": points,
                }
            )

    # Default sort: newer mainstream eras first (MEGA -> SV -> スペシャルBOX -> S&S -> SM -> XY・BW -> 旧裏),
    # then newest release date, then highest reference price.
    items.sort(
        key=lambda item: (
            SERIES_SORT_ORDER.get(item["series"], 99),
            item["release_date"] == "",
            "" if not item["release_date"] else _invert_date(item["release_date"]),
            -item["high_yen"],
            item["name"],
        )
    )

    series_counts: dict[str, int] = {}
    for item in items:
        series_counts[item["series"]] = series_counts.get(item["series"], 0) + 1

    observed_max_stores = max((item["store_count"] for item in items), default=0)
    resolved_store_count = max(active_store_count or 0, observed_max_stores)

    payload: dict[str, Any] = {
        "schema_version": 2,
        "as_of_date": resolved_insights.as_of_date,
        "fetched_at": resolved_insights.fetched_at,
        "anonymized": True,
        "monitored_store_count": resolved_store_count,
        "summary": {
            "total_boxes": len(items),
            "multi_store_boxes": sum(1 for item in items if item["store_count"] >= 2),
            "three_plus_store_boxes": sum(1 for item in items if item["store_count"] >= 3),
            "no_shrink_compared_boxes": sum(
                1 for item in items if item["no_shrink_high_yen"] is not None
            ),
            "history_days": resolved_insights.history_days_available,
            "mood_label": resolved_insights.sentiment.mood_label,
            "mood_summary": resolved_insights.sentiment.mood_summary,
            "prev_up_count": resolved_insights.sentiment.prev_up_count,
            "prev_down_count": resolved_insights.sentiment.prev_down_count,
            "prev_flat_count": resolved_insights.sentiment.prev_flat_count,
            "week_up_count": resolved_insights.sentiment.week_up_count,
            "week_down_count": resolved_insights.sentiment.week_down_count,
            "median_spread_rate": resolved_insights.median_spread_rate,
            "max_spread_rate": resolved_insights.max_spread_rate,
            "max_spread_yen": resolved_insights.max_spread_yen,
            "high_spread_box_count": resolved_insights.high_spread_box_count,
            "series_counts": series_counts,
        },
        "highlights": {
            "prev_gainers": [m.to_dict() for m in resolved_insights.prev_gainers[:5]],
            "prev_losers": [m.to_dict() for m in resolved_insights.prev_losers[:5]],
            "week_gainers": [m.to_dict() for m in resolved_insights.week_gainers[:5]],
            "week_losers": [m.to_dict() for m in resolved_insights.week_losers[:5]],
        },
        "items": items,
    }

    serialized = json.dumps(payload, ensure_ascii=False)
    leaked = find_leaked_store_terms(serialized)
    if leaked:
        raise ValueError(
            f"公開用相場JSONに特定店舗名・ドメインが含まれたため出力を中止しました: {', '.join(leaked)}"
        )
    return payload


def _invert_date(iso_date: str) -> str:
    """Lexicographical inverse of YYYY-MM-DD so ascending tuple sort orders newest first."""
    return "".join(str(9 - int(ch)) if ch.isdigit() else ch for ch in iso_date)


def write_web_market_json(
    output_path: str | Path,
    comparison: pd.DataFrame,
    trend_history: pd.DataFrame | None = None,
    *,
    fetched_at: str | None = None,
    active_store_count: int | None = None,
    insights: MarketInsights | None = None,
) -> Path:
    payload = build_web_market_payload(
        comparison,
        trend_history,
        fetched_at=fetched_at,
        active_store_count=active_store_count,
        insights=insights,
    )
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
