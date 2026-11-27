from __future__ import annotations

import logging
import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..http import PoliteRequester
from ..models import PriceRecord
from ..normalize import (
    build_match_key,
    classify_product_kind,
    clean_text,
    detect_condition,
    parse_price,
)


LOGGER = logging.getLogger(__name__)

CATEGORY_URL = "https://kaitori-rudeya.com/category/detail/114"


def _extract_update_label(soup: BeautifulSoup) -> str:
    text = soup.get_text(" ", strip=True)
    match = re.search(r"(\d{4}年\d{1,2}月\d{1,2}日\s*\d{1,2}時\d{1,2}分現在)", text)
    return clean_text(match.group(1)) if match else ""


def parse_rudeya_html(
    html: str,
    *,
    fetched_at: str,
    page_url: str = CATEGORY_URL,
) -> list[PriceRecord]:
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("article.pgrid-card")
    if not cards:
        raise ValueError("買取ルデヤの商品カード(article.pgrid-card)が見つかりません。")

    update_label = _extract_update_label(soup)
    records: list[PriceRecord] = []
    seen_urls: set[str] = set()

    for card in cards:
        name_link = card.select_one("a.product-card-name-link")
        if not name_link:
            continue
        raw_name = clean_text(name_link.get_text(" ", strip=True))
        if not raw_name:
            continue
        product_url = urljoin(page_url, name_link.get("href", "")) if name_link.get("href") else page_url
        if product_url in seen_urls:
            continue
        seen_urls.add(product_url)

        price_node = card.select_one(".product-card-price-value")
        price = parse_price(price_node.get_text("", strip=True) if price_node else "")
        if price is None or price <= 0:
            continue

        memo_node = card.select_one(".product-card-memo")
        memo_text = clean_text(memo_node.get_text(" ", strip=True) if memo_node else "")
        jan_node = card.select_one(".product-card-jan-text")
        jan_text = clean_text(jan_node.get_text(" ", strip=True) if jan_node else "")

        stopped = bool(card.select_one(".product-card-stopped"))
        stock_status = "out_of_stock" if stopped else "active"

        # Detect explicit condition from product name + official memo ("新品未開封/シュリンク付きのみ").
        condition = detect_condition(f"{raw_name} {memo_text}")
        product_kind = classify_product_kind(raw_name)
        normalized, key = build_match_key(raw_name, condition)
        if not normalized:
            continue

        note_parts: list[str] = []
        if jan_text:
            note_parts.append(jan_text)
        if stopped:
            note_parts.append("お申込一時停止中")

        records.append(
            PriceRecord(
                source="rudeya",
                product_name_raw=raw_name,
                product_name_normalized=normalized,
                match_key=key,
                variant="シュリンク付き" if condition == "shrink_wrapped" else "",
                condition=condition,
                product_kind=product_kind,
                price_yen=price,
                price_min_yen=price,
                price_max_yen=price,
                stock_status=stock_status,
                product_url=product_url,
                source_updated_label=update_label,
                fetched_at=fetched_at,
                notes=" / ".join(note_parts),
            )
        )

    if not records:
        raise ValueError("買取ルデヤ価格表から商品を1件も取得できませんでした。")
    return records


def fetch_rudeya_records(
    requester: PoliteRequester,
    *,
    fetched_at: str | None = None,
) -> list[PriceRecord]:
    timestamp = fetched_at or datetime.now().astimezone().isoformat(timespec="seconds")
    response = requester.get(CATEGORY_URL)
    response.encoding = response.apparent_encoding or "utf-8"
    records = parse_rudeya_html(response.text, fetched_at=timestamp, page_url=response.url)
    LOGGER.info("rudeya: %d件取得", len(records))
    return records
