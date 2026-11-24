from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from statistics import median
from typing import Any

import pandas as pd

from .normalize import normalize_product_name


JAPAN_TIME_ZONE = timezone(timedelta(hours=9), name="JST")

HIGH_SPREAD_RATE_THRESHOLD = 0.05
HIGH_SPREAD_YEN_THRESHOLD = 3_000
DEFAULT_TOP_N = 5

CONDITION_LABELS = {
    "shrink_wrapped": "シュリンク有",
    "no_shrink": "シュリンク無",
    "no_perforation": "ぺりぺり無",
    "unspecified": "状態不明",
    "sealed_unspecified": "未開封（状態不明）",
}


@dataclass(slots=True)
class PriceMover:
    """One box's price movement relative to a prior observation date (store-anonymized)."""

    product_name: str
    latest_price_yen: int
    reference_price_yen: int
    reference_date: str
    diff_yen: int
    diff_rate: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SpreadHighlight:
    """Store-to-store price spread summary for one box without exposing store names."""

    product_name: str
    condition: str
    condition_label: str
    best_price_yen: int
    lowest_price_yen: int
    spread_yen: int
    spread_rate: float
    compared_store_count: int
    condition_inferred: bool
    highlight_reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MarketSentiment:
    """Breadth and tone summary of the shrink-wrapped sealed BOX market."""

    compared_prev_count: int
    prev_up_count: int
    prev_down_count: int
    prev_flat_count: int
    prev_avg_diff_yen: float | None
    prev_avg_diff_rate: float | None
    compared_7d_count: int
    week_up_count: int
    week_down_count: int
    week_flat_count: int
    week_avg_diff_yen: float | None
    week_avg_diff_rate: float | None
    mood_label: str
    mood_summary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MarketInsights:
    """Aggregated, store-anonymized market intelligence extracted from price & trend data."""

    as_of_date: str
    fetched_at: str
    tracked_box_count: int
    multi_store_box_count: int
    history_days_available: int
    sentiment: MarketSentiment
    prev_gainers: list[PriceMover]
    prev_losers: list[PriceMover]
    week_gainers: list[PriceMover]
    week_losers: list[PriceMover]
    spread_by_rate: list[SpreadHighlight]
    spread_by_yen: list[SpreadHighlight]
    combined_spread_highlights: list[SpreadHighlight]
    median_spread_rate: float | None
    max_spread_rate: float | None
    max_spread_yen: int | None
    high_spread_box_count: int
    inferred_spread_excluded_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "as_of_date": self.as_of_date,
            "fetched_at": self.fetched_at,
            "tracked_box_count": self.tracked_box_count,
            "multi_store_box_count": self.multi_store_box_count,
            "history_days_available": self.history_days_available,
            "sentiment": self.sentiment.to_dict(),
            "prev_gainers": [item.to_dict() for item in self.prev_gainers],
            "prev_losers": [item.to_dict() for item in self.prev_losers],
            "week_gainers": [item.to_dict() for item in self.week_gainers],
            "week_losers": [item.to_dict() for item in self.week_losers],
            "spread_by_rate": [item.to_dict() for item in self.spread_by_rate],
            "spread_by_yen": [item.to_dict() for item in self.spread_by_yen],
            "combined_spread_highlights": [
                item.to_dict() for item in self.combined_spread_highlights
            ],
            "median_spread_rate": self.median_spread_rate,
            "max_spread_rate": self.max_spread_rate,
            "max_spread_yen": self.max_spread_yen,
            "high_spread_box_count": self.high_spread_box_count,
            "inferred_spread_excluded_count": self.inferred_spread_excluded_count,
        }


def solve_break_even_selling_price(
    target_net: int, fee_rate: float, fixed_costs: int = 0
) -> int:
    """Match site/js/calculators.js solveBreakEvenSellingPrice for floored fees.

    Finds the minimum integer listing price P such that:
        P - floor(P * fee_rate) - fixed_costs >= target_net
    """
    rate = min(max(float(fee_rate), 0.0), 0.99)
    required = int(target_net) + int(fixed_costs)
    if required <= 0:
        return 0

    price = math.ceil(required / (1.0 - rate))
    while (
        price > 0
        and (price - 1) - math.floor((price - 1) * rate) - fixed_costs >= target_net
    ):
        price -= 1
    while price - math.floor(price * rate) - fixed_costs < target_net:
        price += 1
    return int(price)


def _resolve_as_of_date(fetched_at: str | None, trend_dates: list[str]) -> tuple[str, str]:
    if fetched_at:
        try:
            dt = datetime.fromisoformat(fetched_at).astimezone(JAPAN_TIME_ZONE)
            return dt.date().isoformat(), dt.isoformat(timespec="seconds")
        except ValueError:
            pass
    if trend_dates:
        latest = max(trend_dates)
        return latest, fetched_at or f"{latest}T17:00:00+09:00"
    now_jst = datetime.now(JAPAN_TIME_ZONE)
    return now_jst.date().isoformat(), now_jst.isoformat(timespec="seconds")


def _clean_trend_history(trend_history: pd.DataFrame | None) -> pd.DataFrame:
    """Normalize dates, box names, and integer yen prices from a trend history frame."""
    columns = ["日付", "商品名", "最高値"]
    if trend_history is None or trend_history.empty:
        return pd.DataFrame(columns=columns)
    if not set(columns).issubset(trend_history.columns):
        return pd.DataFrame(columns=columns)

    cleaned = trend_history[columns].copy()
    cleaned["日付"] = cleaned["日付"].astype(str).str.strip()
    cleaned["商品名"] = cleaned["商品名"].astype(str).map(normalize_product_name)
    cleaned["最高値"] = pd.to_numeric(
        cleaned["最高値"].astype(str).str.replace(r"[^0-9.-]", "", regex=True),
        errors="coerce",
    )
    cleaned = cleaned[
        (cleaned["日付"] != "") & (cleaned["商品名"] != "") & cleaned["最高値"].notna()
    ].copy()
    if cleaned.empty:
        return pd.DataFrame(columns=columns)

    cleaned["最高値"] = cleaned["最高値"].astype(int)
    cleaned = cleaned[cleaned["最高値"] > 0]
    cleaned = cleaned.sort_values(
        ["日付", "商品名", "最高値"], ascending=[True, True, False], kind="mergesort"
    )
    return cleaned.drop_duplicates(["日付", "商品名"], keep="first").reset_index(drop=True)


def _classify_sentiment(
    *,
    compared_prev_count: int,
    prev_up_count: int,
    prev_down_count: int,
    prev_flat_count: int,
    compared_7d_count: int,
    week_up_count: int,
    week_down_count: int,
    week_flat_count: int,
) -> tuple[str, str]:
    if compared_prev_count == 0 and compared_7d_count == 0:
        return (
            "履歴蓄積中（初回計測）",
            "前回以前の日次比較履歴がまだないため、2回目以降の更新から値動き地合いが自動判定されます。",
        )

    base_up = prev_up_count if compared_prev_count > 0 else week_up_count
    base_down = prev_down_count if compared_prev_count > 0 else week_down_count
    moved = base_up + base_down
    if moved == 0:
        mood_label = "横ばい・膠着"
    else:
        up_ratio = base_up / moved
        if up_ratio >= 0.65 and (base_up - base_down) >= 2:
            mood_label = "強気（上昇優勢）"
        elif up_ratio > 0.52:
            mood_label = "やや強気（上昇優勢）"
        elif up_ratio <= 0.35 and (base_down - base_up) >= 2:
            mood_label = "弱気（下落優勢）"
        elif up_ratio < 0.48:
            mood_label = "やや弱気（下落優勢）"
        else:
            mood_label = "拮抗・方向感なし"

    parts: list[str] = []
    if compared_prev_count > 0:
        parts.append(
            f"前回比は上昇{prev_up_count}銘柄・下落{prev_down_count}銘柄・横ばい{prev_flat_count}銘柄"
        )
    if compared_7d_count > 0:
        parts.append(
            f"7日前比は上昇{week_up_count}銘柄・下落{week_down_count}銘柄・横ばい{week_flat_count}銘柄"
        )
    detail = "／".join(parts)
    mood_summary = f"{detail}で、相場全体は「{mood_label}」の地合いです。"
    return mood_label, mood_summary


def _spread_reason(spread_rate: float, spread_yen: int) -> str:
    high_rate = spread_rate >= HIGH_SPREAD_RATE_THRESHOLD
    high_yen = spread_yen >= HIGH_SPREAD_YEN_THRESHOLD
    if high_rate and high_yen:
        return "差率5%以上＆差額3,000円以上"
    if high_rate:
        return "差率5%以上"
    if high_yen:
        return "差額3,000円以上"
    return "店舗間差あり"


def _extract_spread_highlights(
    comparison: pd.DataFrame | None,
    *,
    top_n: int,
    include_inferred_spreads: bool,
) -> tuple[
    int,
    list[SpreadHighlight],
    list[SpreadHighlight],
    list[SpreadHighlight],
    float | None,
    float | None,
    int | None,
    int,
    int,
]:
    required = {
        "product_name_normalized",
        "condition",
        "matched_site_count",
        "best_price_yen",
        "spread_yen",
    }
    if comparison is None or comparison.empty or not required.issubset(comparison.columns):
        return 0, [], [], [], None, None, None, 0, 0

    df = comparison.copy()
    df["matched_site_count_num"] = pd.to_numeric(df["matched_site_count"], errors="coerce").fillna(0)
    df["best_price_num"] = pd.to_numeric(df["best_price_yen"], errors="coerce")
    df["spread_num"] = pd.to_numeric(df["spread_yen"], errors="coerce")

    base_mask = (
        (df["condition"] == "shrink_wrapped")
        & (df["matched_site_count_num"] >= 2)
        & df["best_price_num"].notna()
        & (df["best_price_num"] > 0)
        & df["spread_num"].notna()
    )
    multi = df[base_mask].copy()
    multi_store_box_count = len(multi)
    if multi.empty:
        return 0, [], [], [], None, None, None, 0, 0

    inferred_col = (
        multi["condition_inferred"].fillna(False).astype(bool)
        if "condition_inferred" in multi.columns
        else pd.Series(False, index=multi.index)
    )
    multi["_inferred"] = inferred_col
    inferred_excluded = 0
    if not include_inferred_spreads:
        inferred_excluded = int(multi["_inferred"].sum())
        multi = multi[~multi["_inferred"]].copy()

    if multi.empty:
        return multi_store_box_count, [], [], [], None, None, None, 0, inferred_excluded

    highlights: list[SpreadHighlight] = []
    all_rates: list[float] = []
    all_yens: list[int] = []
    high_spread_count = 0

    for _, row in multi.iterrows():
        best_price = int(row["best_price_num"])
        spread_yen = max(0, int(row["spread_num"]))
        spread_rate = round(spread_yen / best_price, 4) if best_price > 0 else 0.0
        all_rates.append(spread_rate)
        all_yens.append(spread_yen)
        if (
            spread_rate >= HIGH_SPREAD_RATE_THRESHOLD
            or spread_yen >= HIGH_SPREAD_YEN_THRESHOLD
        ):
            high_spread_count += 1
        if spread_yen <= 0:
            continue
        cond = str(row["condition"])
        normalized_name = normalize_product_name(str(row["product_name_normalized"]))
        if not normalized_name:
            continue
        highlights.append(
            SpreadHighlight(
                product_name=normalized_name,
                condition=cond,
                condition_label=CONDITION_LABELS.get(cond, cond),
                best_price_yen=best_price,
                lowest_price_yen=max(0, best_price - spread_yen),
                spread_yen=spread_yen,
                spread_rate=spread_rate,
                compared_store_count=int(row["matched_site_count_num"]),
                condition_inferred=bool(row["_inferred"]),
                highlight_reason=_spread_reason(spread_rate, spread_yen),
            )
        )

    by_rate = sorted(
        highlights,
        key=lambda item: (-item.spread_rate, -item.spread_yen, item.product_name),
    )[:top_n]
    by_yen = sorted(
        highlights,
        key=lambda item: (-item.spread_yen, -item.spread_rate, item.product_name),
    )[:top_n]

    # Interleave high-rate and high-yen picks without duplicates so both high-%
    # mid-tier boxes and high-yen vintage boxes appear in content prompts.
    combined: list[SpreadHighlight] = []
    seen_names: set[str] = set()
    limit = max(top_n, 6)
    for idx in range(max(len(by_rate), len(by_yen))):
        for pool in (by_rate, by_yen):
            if idx < len(pool):
                candidate = pool[idx]
                if candidate.product_name not in seen_names:
                    combined.append(candidate)
                    seen_names.add(candidate.product_name)
                    if len(combined) >= limit:
                        break
        if len(combined) >= limit:
            break

    median_rate = round(float(median(all_rates)), 4) if all_rates else None
    max_rate = max(all_rates) if all_rates else None
    max_yen = max(all_yens) if all_yens else None
    return (
        multi_store_box_count,
        by_rate,
        by_yen,
        combined,
        median_rate,
        max_rate,
        max_yen,
        high_spread_count,
        inferred_excluded,
    )


def analyze_market(
    comparison: pd.DataFrame | None,
    trend_history: pd.DataFrame | None,
    *,
    fetched_at: str | None = None,
    top_n: int = DEFAULT_TOP_N,
    include_inferred_spreads: bool = False,
) -> MarketInsights:
    """Extract store-anonymized movers, spread highlights, and market sentiment."""
    top_n = max(1, int(top_n))
    cleaned_trend = _clean_trend_history(trend_history)
    unique_dates = sorted(cleaned_trend["日付"].unique().tolist()) if not cleaned_trend.empty else []
    as_of_date, effective_fetched_at = _resolve_as_of_date(fetched_at, unique_dates)

    prev_movers_all: list[PriceMover] = []
    week_movers_all: list[PriceMover] = []
    prev_up = prev_down = prev_flat = 0
    week_up = week_down = week_flat = 0
    tracked_box_count = 0

    if not cleaned_trend.empty:
        latest_global_iso = unique_dates[-1]
        try:
            target_7d_iso = (date.fromisoformat(latest_global_iso) - timedelta(days=7)).isoformat()
        except ValueError:
            target_7d_iso = ""

        for product_name, group in cleaned_trend.groupby("商品名", sort=True):
            ordered = group.sort_values("日付", kind="mergesort")
            records = list(zip(ordered["日付"].astype(str), ordered["最高値"].astype(int)))
            latest_day, latest_price = records[-1]
            if latest_day != latest_global_iso:
                continue
            tracked_box_count += 1

            if len(records) >= 2:
                prev_day, prev_price = records[-2]
                diff_yen = latest_price - prev_price
                diff_rate = round(diff_yen / prev_price, 4) if prev_price > 0 else 0.0
                if diff_yen > 0:
                    prev_up += 1
                elif diff_yen < 0:
                    prev_down += 1
                else:
                    prev_flat += 1
                prev_movers_all.append(
                    PriceMover(
                        product_name=str(product_name),
                        latest_price_yen=latest_price,
                        reference_price_yen=prev_price,
                        reference_date=prev_day,
                        diff_yen=diff_yen,
                        diff_rate=diff_rate,
                    )
                )

            if target_7d_iso:
                older_or_equal = [
                    (obs_day, price) for obs_day, price in records if obs_day <= target_7d_iso
                ]
                if older_or_equal:
                    ref_day, ref_price = older_or_equal[-1]
                    diff_7d = latest_price - ref_price
                    rate_7d = round(diff_7d / ref_price, 4) if ref_price > 0 else 0.0
                    if diff_7d > 0:
                        week_up += 1
                    elif diff_7d < 0:
                        week_down += 1
                    else:
                        week_flat += 1
                    week_movers_all.append(
                        PriceMover(
                            product_name=str(product_name),
                            latest_price_yen=latest_price,
                            reference_price_yen=ref_price,
                            reference_date=ref_day,
                            diff_yen=diff_7d,
                            diff_rate=rate_7d,
                        )
                    )

    prev_gainers = sorted(
        [m for m in prev_movers_all if m.diff_yen > 0],
        key=lambda m: (-m.diff_rate, -m.diff_yen, m.product_name),
    )[:top_n]
    prev_losers = sorted(
        [m for m in prev_movers_all if m.diff_yen < 0],
        key=lambda m: (m.diff_rate, m.diff_yen, m.product_name),
    )[:top_n]
    week_gainers = sorted(
        [m for m in week_movers_all if m.diff_yen > 0],
        key=lambda m: (-m.diff_rate, -m.diff_yen, m.product_name),
    )[:top_n]
    week_losers = sorted(
        [m for m in week_movers_all if m.diff_yen < 0],
        key=lambda m: (m.diff_rate, m.diff_yen, m.product_name),
    )[:top_n]

    compared_prev_count = len(prev_movers_all)
    compared_7d_count = len(week_movers_all)
    prev_avg_yen = (
        round(sum(m.diff_yen for m in prev_movers_all) / compared_prev_count, 1)
        if compared_prev_count
        else None
    )
    prev_avg_rate = (
        round(sum(m.diff_rate for m in prev_movers_all) / compared_prev_count, 4)
        if compared_prev_count
        else None
    )
    week_avg_yen = (
        round(sum(m.diff_yen for m in week_movers_all) / compared_7d_count, 1)
        if compared_7d_count
        else None
    )
    week_avg_rate = (
        round(sum(m.diff_rate for m in week_movers_all) / compared_7d_count, 4)
        if compared_7d_count
        else None
    )

    mood_label, mood_summary = _classify_sentiment(
        compared_prev_count=compared_prev_count,
        prev_up_count=prev_up,
        prev_down_count=prev_down,
        prev_flat_count=prev_flat,
        compared_7d_count=compared_7d_count,
        week_up_count=week_up,
        week_down_count=week_down,
        week_flat_count=week_flat,
    )
    sentiment = MarketSentiment(
        compared_prev_count=compared_prev_count,
        prev_up_count=prev_up,
        prev_down_count=prev_down,
        prev_flat_count=prev_flat,
        prev_avg_diff_yen=prev_avg_yen,
        prev_avg_diff_rate=prev_avg_rate,
        compared_7d_count=compared_7d_count,
        week_up_count=week_up,
        week_down_count=week_down,
        week_flat_count=week_flat,
        week_avg_diff_yen=week_avg_yen,
        week_avg_diff_rate=week_avg_rate,
        mood_label=mood_label,
        mood_summary=mood_summary,
    )

    (
        multi_store_box_count,
        spread_by_rate,
        spread_by_yen,
        combined_spreads,
        median_spread_rate,
        max_spread_rate,
        max_spread_yen,
        high_spread_box_count,
        inferred_excluded,
    ) = _extract_spread_highlights(
        comparison,
        top_n=top_n,
        include_inferred_spreads=include_inferred_spreads,
    )

    return MarketInsights(
        as_of_date=as_of_date,
        fetched_at=effective_fetched_at,
        tracked_box_count=tracked_box_count,
        multi_store_box_count=multi_store_box_count,
        history_days_available=len(unique_dates),
        sentiment=sentiment,
        prev_gainers=prev_gainers,
        prev_losers=prev_losers,
        week_gainers=week_gainers,
        week_losers=week_losers,
        spread_by_rate=spread_by_rate,
        spread_by_yen=spread_by_yen,
        combined_spread_highlights=combined_spreads,
        median_spread_rate=median_spread_rate,
        max_spread_rate=max_spread_rate,
        max_spread_yen=max_spread_yen,
        high_spread_box_count=high_spread_box_count,
        inferred_spread_excluded_count=inferred_excluded,
    )
