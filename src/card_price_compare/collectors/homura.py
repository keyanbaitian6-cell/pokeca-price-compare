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

PRICE_LIST_URL = "https://kaitori-homura.com/column/2026/10/21/pokemon-box-buyback-price-list/"


def _extract_update_label(soup: BeautifulSoup) -> str:
    text = soup.get_text(" ", strip=True)
    match = re.search(r"価格最終更新\s*(\d{4}年\d{1,2}月\d{1,2}日(?:\s*\d{1,2}:\d{2})?)", text)
    if match:
        return clean_text(match.group(1))
    match = re.search(r"(\d{1,2}/\d{1,2}\s+\d{1,2}:\d{2})更新", text)
    if match:
        return clean_text(match.group(1))
    return ""


def _clean_cell_title(cell: object) -> str:
    """Read product title without inserting spaces across inline nowrap/wbr tags."""
    ttl = cell.select_one(".hmr-hublist__ttl")
    if ttl is not None:
        raw = ttl.get_text("", strip=True)
    else:
        raw = cell.get_text("", strip=True)
    raw = raw.replace("\u2060", "")
    raw = re.sub(r"価格推移・当たり.*", "", raw)
    return clean_text(raw)


def _cell_price_and_url(cell: object, base_url: str) -> tuple[int | None, str, str]:
    link = cell.select_one("a.hmr-hublist__price[href]") or cell.select_one("a[href]")
    price_text = link.get_text("", strip=True) if link else cell.get_text("", strip=True)
    price = parse_price(price_text)
    product_url = urljoin(base_url, link.get("href", "")) if link and link.get("href") else base_url
    notes = "減額ゼロ対象" if cell.select_one(".hmr-hub__fpg") or "減額ゼロ" in cell.get_text("", strip=True) else ""
    return price, product_url, notes


def parse_homura_html(
    html: str,
    *,
    fetched_at: str,
    page_url: str = PRICE_LIST_URL,
) -> list[PriceRecord]:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.select("table")
    if not tables:
        raise ValueError("買取ホムラ価格表のtable要素が見つかりません。")

    update_label = _extract_update_label(soup)
    records: list[PriceRecord] = []
    seen_keys: set[tuple[str, int]] = set()

    for table in tables:
        rows = table.select("tr")
        if len(rows) < 2:
            continue
        headers = [clean_text(cell.get_text("", strip=True)) for cell in rows[0].select("th, td")]
        header_line = " ".join(headers)

        # Standard BOX tables: [画像, BOX, シュリンク有り, シュリンク無し]
        if "BOX" in header_line and "シュリンク" in header_line:
            for tr in rows[1:]:
                cells = tr.select("td")
                if len(cells) < 4:
                    continue
                name_raw = _clean_cell_title(cells[1])
                if not name_raw:
                    continue
                for variant, condition, cell in (
                    ("シュリンク有り", "shrink_wrapped", cells[2]),
                    ("シュリンク無し", "no_shrink", cells[3]),
                ):
                    price, product_url, notes = _cell_price_and_url(cell, page_url)
                    if price is None:
                        continue
                    normalized, key = build_match_key(name_raw, condition)
                    if not normalized or (key, price) in seen_keys:
                        continue
                    seen_keys.add((key, price))
                    records.append(
                        PriceRecord(
                            source="homura",
                            product_name_raw=name_raw,
                            product_name_normalized=normalized,
                            match_key=key,
                            variant=variant,
                            condition=condition,
                            product_kind="sealed_box",
                            price_yen=price,
                            price_min_yen=price,
                            price_max_yen=price,
                            stock_status="active",
                            product_url=product_url,
                            source_updated_label=update_label,
                            fetched_at=fetched_at,
                            notes=notes,
                        )
                    )
            continue

        # Special set / 30th summary tables: [画像, 商品, 買取価格]
        if "商品" in header_line and "買取価格" in header_line:
            for tr in rows[1:]:
                cells = tr.select("td")
                if len(cells) < 3:
                    continue
                name_raw = _clean_cell_title(cells[1])
                if not name_raw:
                    continue
                price, product_url, notes = _cell_price_and_url(cells[2], page_url)
                if price is None:
                    continue
                condition = detect_condition(name_raw)
                # Special BOXes listed on Homura's main buyback page are unopened shrink-wrapped unless stated.
                if condition == "unspecified" and classify_product_kind(name_raw) == "sealed_box":
                    condition = "shrink_wrapped"
                normalized, key = build_match_key(name_raw, condition)
                if not normalized or (key, price) in seen_keys:
                    continue
                seen_keys.add((key, price))
                records.append(
                    PriceRecord(
                        source="homura",
                        product_name_raw=name_raw,
                        product_name_normalized=normalized,
                        match_key=key,
                        variant="",
                        condition=condition,
                        product_kind=classify_product_kind(name_raw),
                        price_yen=price,
                        price_min_yen=price,
                        price_max_yen=price,
                        stock_status="active",
                        product_url=product_url,
                        source_updated_label=update_label,
                        fetched_at=fetched_at,
                        notes=notes,
                    )
                )

    if not records:
        raise ValueError("買取ホムラ価格表から商品を1件も取得できませんでした。")
    return records


def fetch_homura_records(
    requester: PoliteRequester,
    *,
    fetched_at: str | None = None,
) -> list[PriceRecord]:
    timestamp = fetched_at or datetime.now().astimezone().isoformat(timespec="seconds")
    response = requester.get(PRICE_LIST_URL)
    response.encoding = response.apparent_encoding or "utf-8"
    records = parse_homura_html(response.text, fetched_at=timestamp, page_url=response.url)
    LOGGER.info("homura: %d件取得", len(records))
    return records
