from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class PriceItem:
    """1サイト・1商品分の取得レコード。"""

    source_id: str
    source_label: str
    name_raw: str
    name_normalized: str
    condition: str
    price_yen: int | None
    stock_status: str  # "available" | "out_of_stock" | "unknown"
    url: str
    fetched_at: str
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ComparisonRow:
    """複数サイトを横断比較した1商品分の集計結果。"""

    name_normalized: str
    condition: str
    best_price_yen: int
    worst_price_yen: int
    best_sources: list[str]
    spread_yen: int | None
    spread_rate: float | None
    matched_source_count: int
    source_prices: dict[str, int | None] = field(default_factory=dict)
    source_urls: dict[str, str] = field(default_factory=dict)
    target_price_yen: int | None = None
    target_hit: bool = False
    target_diff_yen: int | None = None

    @property
    def best_source_label(self) -> str:
        if not self.best_sources:
            return ""
        return "・".join(self.best_sources)


@dataclass(slots=True)
class AlertRow:
    """目標価格（買い時・売り時）の監視結果。"""

    item_name: str
    condition: str
    target_price_yen: int
    current_best_yen: int | None
    best_source_label: str
    diff_yen: int | None
    achieved: bool
    status_label: str
    url: str = ""
