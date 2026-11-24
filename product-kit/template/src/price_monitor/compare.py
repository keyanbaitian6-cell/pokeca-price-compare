from __future__ import annotations

from collections import defaultdict

from .config import AlertTarget, AppConfig
from .models import AlertRow, ComparisonRow, PriceItem
from .normalize import normalize_name


def _find_target(
    name_normalized: str,
    condition: str,
    targets: list[tuple[str, AlertTarget]],
) -> AlertTarget | None:
    lowered = name_normalized.lower()
    # 条件一致を優先し、条件未指定のターゲットへフォールバック
    for target_norm, target in targets:
        if target_norm.lower() == lowered and target.condition and target.condition == condition:
            return target
    for target_norm, target in targets:
        if target_norm.lower() == lowered and not target.condition:
            return target
    return None


def _evaluate_target(mode: str, best_price: int, target_price: int) -> tuple[bool, int]:
    """目標達成かどうかの判定と、目標に対する差額を返す。

    lowest（安く買う）: best_price <= target_price で達成。diff = best_price - target_price（マイナスほどお得）
    highest（高く売る）: best_price >= target_price で達成。diff = best_price - target_price（プラスほどお得）
    """
    diff = best_price - target_price
    achieved = (best_price <= target_price) if mode == "lowest" else (best_price >= target_price)
    return achieved, diff


def build_comparison(
    items: list[PriceItem],
    config: AppConfig,
) -> tuple[list[ComparisonRow], list[ComparisonRow], list[AlertRow]]:
    """全取得レコードから (複数サイト比較行, 単独掲載行, 目標アラート行) を構築する。"""
    mode = config.project.comparison_mode
    enabled_sources = config.enabled_sources
    source_label_by_id = {source.id: source.label for source in enabled_sources}
    source_order = [source.id for source in enabled_sources]

    prepared_targets = [
        (normalize_name(target.item, config.normalization) or target.item, target)
        for target in config.alerts.targets
    ]

    # (name_normalized, condition) -> source_id -> (price_yen, url)
    grouped: dict[tuple[str, str], dict[str, tuple[int, str]]] = defaultdict(dict)

    for item in items:
        if item.stock_status == "out_of_stock":
            continue
        if item.price_yen is None or item.price_yen <= 0:
            continue
        norm_name = item.name_normalized or normalize_name(item.name_raw, config.normalization)
        if not norm_name:
            continue

        key = (norm_name, item.condition or "標準")
        existing = grouped[key].get(item.source_id)
        if existing is None:
            grouped[key][item.source_id] = (item.price_yen, item.url)
        else:
            prev_price, _ = existing
            is_better = (item.price_yen < prev_price) if mode == "lowest" else (item.price_yen > prev_price)
            if is_better:
                grouped[key][item.source_id] = (item.price_yen, item.url)

    all_rows: list[ComparisonRow] = []
    for (norm_name, condition), price_map in grouped.items():
        if not price_map:
            continue

        ordered_prices = {sid: (price_map[sid][0] if sid in price_map else None) for sid in source_order}
        ordered_urls = {sid: (price_map[sid][1] if sid in price_map else "") for sid in source_order}
        # もし有効リスト外のsource_idが混在しても落とさない
        for sid, (price, url) in price_map.items():
            if sid not in ordered_prices:
                ordered_prices[sid] = price
                ordered_urls[sid] = url

        valid_entries = [(sid, price) for sid, price in ordered_prices.items() if price is not None]
        prices_only = [price for _, price in valid_entries]
        min_price = min(prices_only)
        max_price = max(prices_only)
        best_price = min_price if mode == "lowest" else max_price
        worst_price = max_price if mode == "lowest" else min_price

        best_source_labels = [
            source_label_by_id.get(sid, sid)
            for sid, price in valid_entries
            if price == best_price
        ]
        matched_count = len(valid_entries)
        spread_yen = (max_price - min_price) if matched_count >= 2 else None
        spread_rate = (spread_yen / max_price) if (spread_yen is not None and max_price > 0) else None

        target = _find_target(norm_name, condition, prepared_targets)
        target_price = target.target_price_yen if target else None
        target_hit = False
        target_diff = None
        if target_price is not None:
            target_hit, target_diff = _evaluate_target(mode, best_price, target_price)

        all_rows.append(
            ComparisonRow(
                name_normalized=norm_name,
                condition=condition,
                best_price_yen=best_price,
                worst_price_yen=worst_price,
                best_sources=best_source_labels,
                spread_yen=spread_yen,
                spread_rate=spread_rate,
                matched_source_count=matched_count,
                source_prices=ordered_prices,
                source_urls=ordered_urls,
                target_price_yen=target_price,
                target_hit=target_hit,
                target_diff_yen=target_diff,
            )
        )

    compared_rows = [row for row in all_rows if row.matched_source_count >= 2]
    single_rows = [row for row in all_rows if row.matched_source_count == 1]

    compared_rows.sort(
        key=lambda row: (
            -(row.spread_rate or 0.0),
            -(row.spread_yen or 0),
            row.name_normalized,
            row.condition,
        )
    )
    single_rows.sort(
        key=lambda row: (
            row.best_price_yen if mode == "lowest" else -row.best_price_yen,
            row.name_normalized,
        )
    )

    # 目標アラート一覧（設定された全ターゲットについて現在状況を集計）
    alert_rows: list[AlertRow] = []
    for target_norm, target in prepared_targets:
        matched_rows = [
            row
            for row in all_rows
            if row.name_normalized.lower() == target_norm.lower()
            and (not target.condition or row.condition == target.condition)
        ]
        if not matched_rows:
            alert_rows.append(
                AlertRow(
                    item_name=target_norm,
                    condition=target.condition or "指定なし",
                    target_price_yen=target.target_price_yen,
                    current_best_yen=None,
                    best_source_label="",
                    diff_yen=None,
                    achieved=False,
                    status_label="未検出（在庫切れ含む）",
                    url="",
                )
            )
            continue

        chosen = (
            min(matched_rows, key=lambda r: r.best_price_yen)
            if mode == "lowest"
            else max(matched_rows, key=lambda r: r.best_price_yen)
        )
        achieved, diff_yen = _evaluate_target(mode, chosen.best_price_yen, target.target_price_yen)
        best_url = ""
        for sid, price in chosen.source_prices.items():
            if price == chosen.best_price_yen and chosen.source_urls.get(sid):
                best_url = chosen.source_urls[sid]
                break
        alert_rows.append(
            AlertRow(
                item_name=chosen.name_normalized,
                condition=chosen.condition,
                target_price_yen=target.target_price_yen,
                current_best_yen=chosen.best_price_yen,
                best_source_label=chosen.best_source_label,
                diff_yen=diff_yen,
                achieved=achieved,
                status_label="🎯 目標達成" if achieved else "監視中",
                url=best_url,
            )
        )

    alert_rows.sort(
        key=lambda row: (
            0 if row.achieved else (1 if row.current_best_yen is not None else 2),
            abs(row.diff_yen) if row.diff_yen is not None else 10**12,
            row.item_name,
        )
    )

    return compared_rows, single_rows, alert_rows
