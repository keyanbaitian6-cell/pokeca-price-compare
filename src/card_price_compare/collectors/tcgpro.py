from __future__ import annotations

import logging
import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..http import PoliteRequester
from ..models import PriceRecord
from ..normalize import build_match_key, clean_text, parse_price


LOGGER = logging.getLogger(__name__)

PRICE_LIST_URL = "https://tcgpro.co.jp/box-kaitori/"


def _extract_update_label(soup: BeautifulSoup) -> str:
    text = soup.get_text(" ", strip=True)
    match = re.search(r"(\d{4}年\d{1,2}月\d{1,2}日)更新", text)
    return clean_text(match.group(1)) if match else ""


def _format_release_date(raw_date: str) -> str:
    digits = re.sub(r"\D", "", raw_date or "")
    if len(digits) == 8:
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
    return ""


def parse_tcgpro_html(
    html: str,
    *,
    fetched_at: str,
    page_url: str = PRICE_LIST_URL,
) -> list[PriceRecord]:
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("li.kb-item[data-price]")
    if not items:
        raise ValueError("トレカプロBOX買取表の商品要素(li.kb-item)が見つかりません。")

    update_label = _extract_update_label(soup)
    records: list[PriceRecord] = []

    for item in items:
        price = parse_price(str(item.get("data-price", "")))
        if price is None or price <= 0:
            continue

        link = item.select_one("a.kb-item__link[href]") or item.select_one("a[href]")
        product_url = (
            urljoin(page_url, link.get("href", ""))
            if link and link.get("href")
            else page_url
        )

        # Prefer data-q (contains exact set name + official set code), falling back to aria-label.
        raw_name = clean_text(str(item.get("data-q", "")))
        if not raw_name and link and link.get("aria-label"):
            raw_name = clean_text(re.sub(r"（買取価格.*$", "", str(link.get("aria-label"))))
        if not raw_name:
            continue

        condition = "shrink_wrapped"
        normalized, key = build_match_key(raw_name, condition)
        if not normalized:
            continue

        note_parts: list[str] = []
        cat = clean_text(str(item.get("data-cat", "")))
        if cat:
            note_parts.append(f"区分:{cat}")
        release_date = _format_release_date(str(item.get("data-date", "")))
        if release_date:
            note_parts.append(f"発売日:{release_date}")

        records.append(
            PriceRecord(
                source="tcgpro",
                product_name_raw=raw_name,
                product_name_normalized=normalized,
                match_key=key,
                variant="シュリンク付き",
                condition=condition,
                product_kind="sealed_box",
                price_yen=price,
                price_min_yen=price,
                price_max_yen=price,
                stock_status="active",
                product_url=product_url,
                source_updated_label=update_label,
                fetched_at=fetched_at,
                notes=" / ".join(note_parts),
            )
        )

    if not records:
        raise ValueError("トレカプロBOX買取表から商品を1件も取得できませんでした。")
    return records


def fetch_tcgpro_records(
    requester: PoliteRequester,
    *,
    fetched_at: str | None = None,
) -> list[PriceRecord]:
    timestamp = fetched_at or datetime.now().astimezone().isoformat(timespec="seconds")
    response = requester.get(PRICE_LIST_URL)
    response.encoding = response.apparent_encoding or "utf-8"
    records = parse_tcgpro_html(response.text, fetched_at=timestamp, page_url=response.url)
    LOGGER.info("tcgpro: %d件取得", len(records))
    return records
