from __future__ import annotations

import json
import logging
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
    parse_price_range,
)


LOGGER = logging.getLogger(__name__)

CATEGORY_URL = "https://runto666.com/product-category/card/"


def _select_labels(form: object) -> dict[str, dict[str, str]]:
    labels: dict[str, dict[str, str]] = {}
    for select in form.select("select[name]"):
        labels[select.get("name", "")] = {
            option.get("value", ""): clean_text(option.get_text(" ", strip=True))
            for option in select.select("option[value]")
            if option.get("value")
        }
    return labels


def parse_runto_product_html(
    html: str,
    *,
    product_url: str,
    fallback_name: str,
    stock_status: str,
    fetched_at: str,
) -> list[PriceRecord]:
    soup = BeautifulSoup(html, "html.parser")
    title_node = soup.select_one("h1.product_title")
    product_name = clean_text(title_node.get_text(" ", strip=True) if title_node else fallback_name)
    form = soup.select_one("form.variations_form[data-product_variations]")

    if form:
        try:
            variations = json.loads(form.get("data-product_variations", "[]"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"runtoの商品バリエーションJSONを解析できません: {product_url}") from exc
        label_maps = _select_labels(form)
        records: list[PriceRecord] = []
        for variation in variations:
            attributes = variation.get("attributes") or {}
            variant_parts = []
            for attribute_name, attribute_value in attributes.items():
                variant_parts.append(label_maps.get(attribute_name, {}).get(attribute_value, attribute_value))
            variant = " / ".join(part for part in variant_parts if part)
            combined = f"{product_name} {variant}"
            condition = detect_condition(combined)
            price = parse_price(str(variation.get("display_price", "")))
            if price is None:
                continue
            variation_stock = "active" if variation.get("is_in_stock", True) else "out_of_stock"
            normalized, key = build_match_key(product_name, condition)
            records.append(
                PriceRecord(
                    source="runto",
                    product_name_raw=product_name,
                    product_name_normalized=normalized,
                    match_key=key,
                    variant=variant,
                    condition=condition,
                    product_kind=classify_product_kind(combined),
                    price_yen=price,
                    price_min_yen=price,
                    price_max_yen=price,
                    stock_status=variation_stock,
                    product_url=product_url,
                    source_updated_label="",
                    fetched_at=fetched_at,
                )
            )
        return records

    price_node = soup.select_one(".summary .price")
    price_text = clean_text(price_node.get_text(" ", strip=True) if price_node else "")
    price_min, price_max = parse_price_range(price_text)
    exact_price = price_min if price_min == price_max else None
    condition = detect_condition(product_name)
    normalized, key = build_match_key(product_name, condition)
    return [
        PriceRecord(
            source="runto",
            product_name_raw=product_name,
            product_name_normalized=normalized,
            match_key=key,
            variant="",
            condition=condition,
            product_kind=classify_product_kind(product_name),
            price_yen=exact_price,
            price_min_yen=price_min,
            price_max_yen=price_max,
            stock_status=stock_status,
            product_url=product_url,
            source_updated_label="",
            fetched_at=fetched_at,
        )
    ]


def _parse_listing(html: str, page_url: str) -> tuple[list[dict[str, str | bool]], str | None]:
    soup = BeautifulSoup(html, "html.parser")
    products: list[dict[str, str | bool]] = []
    for item in soup.select("li.product"):
        title_node = item.select_one(".woocommerce-loop-product__title")
        product_link = item.select_one("a.woocommerce-LoopProduct-link[href]")
        price_node = item.select_one(".price")
        if not title_node or not product_link:
            continue
        classes = set(item.get("class", []))
        products.append(
            {
                "name": clean_text(title_node.get_text(" ", strip=True)),
                "url": urljoin(page_url, product_link.get("href", "")),
                "price_text": clean_text(price_node.get_text(" ", strip=True) if price_node else ""),
                "variable": "product-type-variable" in classes,
                "stock_status": "out_of_stock" if "outofstock" in classes else "active",
            }
        )
    next_link = soup.select_one("a.next.page-numbers[href], a.next[href]")
    return products, urljoin(page_url, next_link.get("href")) if next_link else None


def fetch_runto_records(
    requester: PoliteRequester,
    *,
    max_pages: int | None = None,
    resolve_variants: bool = True,
    fetched_at: str | None = None,
) -> list[PriceRecord]:
    timestamp = fetched_at or datetime.now().astimezone().isoformat(timespec="seconds")
    page_url: str | None = CATEGORY_URL
    page_number = 0
    detail_number = 0
    records: list[PriceRecord] = []
    visited: set[str] = set()

    while page_url and page_url not in visited:
        if max_pages is not None and page_number >= max_pages:
            break
        visited.add(page_url)
        response = requester.get(page_url)
        products, page_url = _parse_listing(response.text, response.url)
        page_number += 1
        # One polite request per second means this collector is silent for over
        # a minute. Log the progress so a normal run is not mistaken for a hang.
        LOGGER.info("runto: 一覧%dページ目 商品%d件", page_number, len(products))

        for product in products:
            name = str(product["name"])
            url = str(product["url"])
            status = str(product["stock_status"])
            if bool(product["variable"]) and resolve_variants and classify_product_kind(name) == "sealed_box":
                detail_number += 1
                LOGGER.info("runto: 商品詳細%d件目 %s", detail_number, name)
                detail = requester.get(url)
                records.extend(
                    parse_runto_product_html(
                        detail.text,
                        product_url=url,
                        fallback_name=name,
                        stock_status=status,
                        fetched_at=timestamp,
                    )
                )
                continue

            price_min, price_max = parse_price_range(str(product["price_text"]))
            exact_price = price_min if price_min == price_max else None
            condition = detect_condition(name)
            normalized, key = build_match_key(name, condition)
            records.append(
                PriceRecord(
                    source="runto",
                    product_name_raw=name,
                    product_name_normalized=normalized,
                    match_key=key,
                    variant="",
                    condition=condition,
                    product_kind=classify_product_kind(name),
                    price_yen=exact_price,
                    price_min_yen=price_min,
                    price_max_yen=price_max,
                    stock_status=status,
                    product_url=url,
                    source_updated_label="",
                    fetched_at=timestamp,
                )
            )
    LOGGER.info("runto: 一覧%dページ・商品詳細%d件から%d件取得", page_number, detail_number, len(records))
    return records

