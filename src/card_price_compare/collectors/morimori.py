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

# Pokémon TCG BOX subcategories on Morimori (excludes PSA/single-card category 2401009).
CATEGORY_URLS: tuple[str, ...] = (
    "https://www.morimori-kaitori.jp/category/price-list/2401010",  # MEGA
    "https://www.morimori-kaitori.jp/category/price-list/2401001",  # Scarlet & Violet
    "https://www.morimori-kaitori.jp/category/price-list/2401002",  # Sword & Shield
)


def _extract_update_label(soup: BeautifulSoup) -> str:
    text = soup.get_text(" ", strip=True)
    match = re.search(r"(\d{4}年\d{1,2}月\d{1,2}日)", text)
    return clean_text(match.group(1)) if match else ""


def _clean_morimori_name(raw_cell_text: str) -> str:
    # Morimori prefixes the product name cell with brand text such as "ポケモン\n商品名".
    lines = [clean_text(line) for line in raw_cell_text.splitlines() if clean_text(line)]
    if len(lines) >= 2 and lines[0] in {"ポケモン", "ポケモンカード", "ポケモンカードゲーム"}:
        text = " ".join(lines[1:])
    else:
        text = clean_text(raw_cell_text)
    text = re.sub(r"^新品\s*", "", text)
    text = re.sub(r"^ポケモン\s+(?=(?:ポケモン|MEGA|メガ|ブラック|ホワイト|ロケット|熱風|ニンジャ|インフェルノ|クレイ|サイバー|ステラ|テラスタル|トリプレット|白熱|楽園|pokemone))", "", text, flags=re.IGNORECASE)
    return clean_text(text)


def parse_morimori_html(
    html: str,
    *,
    fetched_at: str,
    page_url: str,
) -> list[PriceRecord]:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.select("table")
    if not tables:
        return []

    update_label = _extract_update_label(soup)
    # The first table is the desktop layout; the second table duplicates the same rows for mobile.
    table = tables[0]
    rows = table.select("tr")
    if len(rows) < 2:
        return []

    records: list[PriceRecord] = []
    for tr in rows[1:]:
        cells = tr.select("td")
        if len(cells) < 7:
            continue
        series_label = clean_text(cells[2].get_text(" ", strip=True))
        item_type = clean_text(cells[3].get_text(" ", strip=True))
        if item_type and item_type != "新品":
            continue

        name_cell = cells[4]
        link = name_cell.select_one("a[href]")
        product_url = (
            urljoin(page_url, link.get("href", ""))
            if link and link.get("href")
            else page_url
        )
        raw_name = _clean_morimori_name(name_cell.get_text("\n"))
        if not raw_name:
            continue
        if any(marker in raw_name.upper() for marker in ("PSA", "シングル")):
            continue

        jan = clean_text(cells[5].get_text(" ", strip=True))
        # Column 6 is 通常買取価格 (standard buyback price, excluding 3-month custody bonus).
        price = parse_price(cells[6].get_text(" ", strip=True))
        if price is None or price <= 0:
            continue

        # Exclude cartons/non-box listings cleanly (e.g. "シャイニースターV carton").
        product_kind = classify_product_kind(raw_name)
        if product_kind == "unknown":
            # Morimori's MEGA/SV/S&S subcategories are sealed BOX lists even if "BOX" is omitted.
            product_kind = "sealed_box"
        if product_kind != "sealed_box":
            continue

        condition = detect_condition(raw_name)
        if condition == "unspecified":
            # Morimori's "新品" Pokémon BOX listings require unopened shrink-wrap.
            condition = "shrink_wrapped"

        normalized, key = build_match_key(raw_name, condition)
        if not normalized:
            continue

        note_parts = [f"通常買取({series_label})" if series_label else "通常買取"]
        if jan:
            note_parts.append(f"JAN:{jan}")

        records.append(
            PriceRecord(
                source="morimori",
                product_name_raw=raw_name,
                product_name_normalized=normalized,
                match_key=key,
                variant="通常買取",
                condition=condition,
                product_kind=product_kind,
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
    return records


def fetch_morimori_records(
    requester: PoliteRequester,
    *,
    fetched_at: str | None = None,
) -> list[PriceRecord]:
    timestamp = fetched_at or datetime.now().astimezone().isoformat(timespec="seconds")
    records: list[PriceRecord] = []
    for url in CATEGORY_URLS:
        response = requester.get(url)
        response.encoding = response.apparent_encoding or "utf-8"
        page_records = parse_morimori_html(response.text, fetched_at=timestamp, page_url=response.url)
        LOGGER.info("morimori: %s -> %d件", url, len(page_records))
        records.extend(page_records)
    if not records:
        raise ValueError("森森買取のポケカBOX価格表から商品を1件も取得できませんでした。")
    LOGGER.info("morimori: 合計%d件取得", len(records))
    return records
