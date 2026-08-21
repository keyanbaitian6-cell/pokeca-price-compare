from __future__ import annotations

"""Collector for the public buyback list published by 買取マッチョ.

The page is currently server-rendered, so requests is sufficient.  The cards
do not expose individual product links; keep the list URL as the source link
until the site provides detail pages.
"""

from datetime import datetime

from bs4 import BeautifulSoup

from ..http import PoliteRequester
from ..models import PriceRecord
from ..normalize import build_match_key, clean_text, parse_price


BUYBACK_PRICES_URL = "https://kaitori.alc-japan.co.jp/buyback-prices"
PACK_BUYBACK_MAX_YEN = 800

_CARD_SELECTOR = "div.flex.flex-col.rounded-xl.border-2"
_CONDITION_BY_BADGE = {
    "シュリンク有": "shrink_wrapped",
    "シュリンク無": "no_shrink",
    "ペリ無": "no_perforation",
}
_PACK_BADGES = {"パック", "統一パック"}


def _card_badges(card: object) -> list[str]:
    """Return the small category/condition badges shown on a price card."""
    return [clean_text(node.get_text(" ", strip=True)) for node in card.select("span")]


def parse_macho_buyback_html(
    html: str,
    *,
    product_url: str = BUYBACK_PRICES_URL,
    fetched_at: str,
) -> list[PriceRecord]:
    """Parse the current product-card layout without relying on card order."""
    soup = BeautifulSoup(html, "html.parser")
    records: list[PriceRecord] = []

    for card in soup.select(_CARD_SELECTOR):
        # The product-name button is intentionally selected by its line-clamp
        # class: the other buttons are cart controls (minus, plus, add).
        name_node = card.select_one("button.line-clamp-2")
        price_node = card.select_one("span.font-mono.font-black")
        if not name_node or not price_node:
            continue
        product_name = clean_text(name_node.get_text(" ", strip=True))
        price = parse_price(price_node.get_text(" ", strip=True))
        if not product_name or price is None:
            continue

        badges = _card_badges(card)
        variant_badges = [
            badge for badge in badges if badge in _CONDITION_BY_BADGE or badge in _PACK_BADGES
        ]
        variant = " / ".join(variant_badges)
        condition = next(
            (_CONDITION_BY_BADGE[badge] for badge in variant_badges if badge in _CONDITION_BY_BADGE),
            "unspecified",
        )

        # The board lists BOX and pack buyback rows together.  Explicit pack
        # badges are never compared as a BOX, even for a high-priced uniform
        # pack.  The 800-yen ceiling is a defensive fallback for a regular
        # pack whose badge is temporarily omitted by a future page redesign.
        is_pack_buyback = price <= PACK_BUYBACK_MAX_YEN or any(
            badge in _PACK_BADGES for badge in variant_badges
        )
        product_kind = "single_pack" if is_pack_buyback else (
            "sealed_box" if condition in _CONDITION_BY_BADGE.values() else "sealed_other"
        )
        normalized, key = build_match_key(product_name, condition)
        notes = "レシート同封必須" if any("レシート同封必須" in badge for badge in badges) else ""
        records.append(
            PriceRecord(
                source="macho",
                product_name_raw=product_name,
                product_name_normalized=normalized,
                match_key=key,
                variant=variant,
                condition=condition,
                product_kind=product_kind,
                price_yen=price,
                price_min_yen=price,
                price_max_yen=price,
                stock_status="active",
                product_url=product_url,
                source_updated_label="",
                fetched_at=fetched_at,
                notes=notes,
            )
        )
    return records


def fetch_macho_records(
    requester: PoliteRequester,
    *,
    fetched_at: str | None = None,
) -> list[PriceRecord]:
    """Fetch 買取マッチョ's one public buyback-price page."""
    timestamp = fetched_at or datetime.now().astimezone().isoformat(timespec="seconds")
    response = requester.get(BUYBACK_PRICES_URL)
    records = parse_macho_buyback_html(
        response.text,
        product_url=response.url,
        fetched_at=timestamp,
    )
    if not records:
        raise RuntimeError("買取マッチョから商品を1件も取得できませんでした。")
    return records
