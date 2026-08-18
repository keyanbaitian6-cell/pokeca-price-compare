from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class PriceRecord:
    """One store price for one product/condition combination."""

    source: str
    product_name_raw: str
    product_name_normalized: str
    match_key: str
    variant: str
    condition: str
    product_kind: str
    price_yen: int | None
    price_min_yen: int | None
    price_max_yen: int | None
    stock_status: str
    product_url: str
    source_updated_label: str
    fetched_at: str
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

