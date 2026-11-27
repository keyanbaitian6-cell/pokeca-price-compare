from __future__ import annotations

from statistics import median

import pandas as pd

from .models import PriceRecord
from .normalize import normalize_product_name
from .stores import ALL_SOURCE_ORDER


SOURCE_ORDER = list(ALL_SOURCE_ORDER)
ACTUAL_CONDITIONS = {"shrink_wrapped", "no_shrink", "no_perforation"}
UNSPECIFIED_CONDITIONS = {"unspecified", "sealed_unspecified"}
COMPARABLE_CONDITIONS = ACTUAL_CONDITIONS | UNSPECIFIED_CONDITIONS


def records_to_frame(records: list[PriceRecord]) -> pd.DataFrame:
    columns = list(PriceRecord.__dataclass_fields__)
    return pd.DataFrame([record.to_dict() for record in records], columns=columns)


def build_box_comparison(raw: pd.DataFrame) -> pd.DataFrame:
    price_columns = [f"{source}_price_yen" for source in SOURCE_ORDER]
    name_columns = [f"{source}_name" for source in SOURCE_ORDER]
    output_columns = [
        "product_name_normalized",
        "condition",
        "condition_inferred",
        *price_columns,
        "best_site",
        "best_price_yen",
        "lowest_price_yen",
        "median_price_yen",
        "second_best_price_yen",
        "top_lead_yen",
        "spread_yen",
        "matched_site_count",
        *name_columns,
    ]
    if raw.empty:
        return pd.DataFrame(columns=output_columns)

    eligible = raw[
        (raw["product_kind"] == "sealed_box")
        & (raw["condition"].isin(COMPARABLE_CONDITIONS))
        & (raw["stock_status"] == "active")
        & raw["price_yen"].notna()
    ].copy()
    if eligible.empty:
        return pd.DataFrame(columns=output_columns)

    eligible["price_yen"] = eligible["price_yen"].astype("int64")
    # Recompute from the raw name so an old raw CSV can be reprocessed after a
    # normalization-rule fix without scraping the source sites again.
    eligible["product_name_normalized"] = eligible["product_name_raw"].map(normalize_product_name)
    eligible = eligible[eligible["product_name_normalized"] != ""].copy()

    # An unspecified row may participate in every known condition for the same
    # product. This deliberately duplicates the unknown price across condition
    # rows and marks those comparisons as inferred. A real condition from the
    # same source always wins over its duplicated unknown row.
    expanded_groups: list[pd.DataFrame] = []
    for _, group in eligible.groupby("product_name_normalized", sort=False):
        actual = group[group["condition"].isin(ACTUAL_CONDITIONS)].copy()
        unknown = group[group["condition"].isin(UNSPECIFIED_CONDITIONS)].copy()
        actual_conditions = sorted(actual["condition"].unique())

        if not actual.empty:
            actual["comparison_condition"] = actual["condition"]
            actual["condition_inferred"] = False
            expanded_groups.append(actual)

        if unknown.empty:
            continue
        if actual_conditions:
            for condition in actual_conditions:
                inferred = unknown.copy()
                inferred["comparison_condition"] = condition
                inferred["condition_inferred"] = True
                expanded_groups.append(inferred)
        else:
            unknown["comparison_condition"] = "unspecified"
            unknown["condition_inferred"] = False
            expanded_groups.append(unknown)

    if not expanded_groups:
        return pd.DataFrame(columns=output_columns)

    expanded = pd.concat(expanded_groups, ignore_index=True)
    expanded["comparison_key"] = (
        expanded["product_name_normalized"] + "|" + expanded["comparison_condition"]
    )
    priority = expanded["condition_inferred"].astype("int8")
    best_priority = priority.groupby([expanded["comparison_key"], expanded["source"]]).transform("min")
    effective = expanded[priority == best_priority].copy()

    prices = effective.pivot_table(
        index="comparison_key", columns="source", values="price_yen", aggfunc="max"
    )
    names = effective.pivot_table(
        index="comparison_key",
        columns="source",
        values="product_name_raw",
        aggfunc=lambda values: " / ".join(sorted(set(values))),
    )

    result = pd.DataFrame(index=prices.index)
    representative = effective.drop_duplicates("comparison_key").set_index("comparison_key")
    result["product_name_normalized"] = representative["product_name_normalized"]
    result["condition"] = representative["comparison_condition"]
    result["condition_inferred"] = effective.groupby("comparison_key")["condition_inferred"].any()
    for source in SOURCE_ORDER:
        price_values = prices[source] if source in prices else pd.Series(pd.NA, index=result.index)
        result[f"{source}_price_yen"] = price_values.astype("Int64")
        result[f"{source}_name"] = names[source] if source in names else pd.NA

    result["matched_site_count"] = result[price_columns].notna().sum(axis=1)
    result["best_price_yen"] = result[price_columns].max(axis=1, skipna=True).astype("Int64")
    result["lowest_price_yen"] = result[price_columns].min(axis=1, skipna=True).astype("Int64")

    def _row_values(row: pd.Series) -> list[int]:
        return [int(row[column]) for column in price_columns if pd.notna(row[column])]

    def best_site(row: pd.Series) -> str:
        candidates = {
            source: int(row[f"{source}_price_yen"])
            for source in SOURCE_ORDER
            if pd.notna(row[f"{source}_price_yen"])
        }
        if not candidates:
            return ""
        best = max(candidates.values())
        return ",".join(source for source, price in candidates.items() if price == best)

    def spread(row: pd.Series) -> int | None:
        values = _row_values(row)
        return max(values) - min(values) if len(values) >= 2 else None

    def median_price(row: pd.Series) -> int | None:
        values = _row_values(row)
        return int(round(median(values))) if values else None

    def second_best(row: pd.Series) -> int | None:
        values = sorted(_row_values(row), reverse=True)
        return values[1] if len(values) >= 2 else None

    def top_lead(row: pd.Series) -> int | None:
        values = sorted(_row_values(row), reverse=True)
        return values[0] - values[1] if len(values) >= 2 else None

    result["best_site"] = result.apply(best_site, axis=1)
    result["spread_yen"] = result.apply(spread, axis=1).astype("Int64")
    result["median_price_yen"] = result.apply(median_price, axis=1).astype("Int64")
    result["second_best_price_yen"] = result.apply(second_best, axis=1).astype("Int64")
    result["top_lead_yen"] = result.apply(top_lead, axis=1).astype("Int64")
    result = result.reset_index(drop=True)
    result = result[output_columns]
    return result.sort_values(
        ["matched_site_count", "product_name_normalized", "condition"],
        ascending=[False, True, True],
    ).reset_index(drop=True)
