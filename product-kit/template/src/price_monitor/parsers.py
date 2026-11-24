from __future__ import annotations

import csv
import importlib.util
import io
import json
import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from .config import AppConfig, SourceConfig
from .http_client import PoliteHttpClient
from .models import PriceItem
from .normalize import normalize_name, parse_price_yen


LOGGER = logging.getLogger(__name__)
VALID_COLLECTOR_NAME_RE = re.compile(r"^[a-zA-Z0-9_]+$")


def _detect_stock_status(text: str, stock_out_keywords: list[str]) -> str:
    lowered = text.lower()
    for keyword in stock_out_keywords:
        if keyword.lower() in lowered:
            return "out_of_stock"
    return "available"


def _select_text(node: Tag | BeautifulSoup, selector: str) -> str:
    if not selector:
        return ""
    found = node.select_one(selector)
    if found is None:
        return ""
    return found.get_text(" ", strip=True)


def _select_link(node: Tag | BeautifulSoup, selector: str, base_url: str) -> str:
    if not selector:
        return base_url
    found = node.select_one(selector)
    if found is None:
        return base_url
    href = str(found.get("href") or "").strip()
    if not href:
        return base_url
    if urlparse(base_url).scheme in {"http", "https"}:
        return urljoin(base_url, href)
    return href


def _parse_html_list_page(
    html: str,
    *,
    source: SourceConfig,
    config: AppConfig,
    page_url: str,
    fetched_at: str,
) -> tuple[list[PriceItem], str | None]:
    soup = BeautifulSoup(html, "html.parser")
    selectors = source.selectors
    item_selector = selectors.get("item", "").strip()
    name_selector = selectors.get("name", "").strip()
    price_selector = selectors.get("price", "").strip()
    if not (item_selector and name_selector and price_selector):
        raise ValueError(
            f"取得元 '{source.id}' (html_list) には selectors.item / name / price が必要です。"
        )

    items: list[PriceItem] = []
    for card in soup.select(item_selector):
        name_raw = _select_text(card, name_selector)
        if not name_raw:
            continue
        price_raw = _select_text(card, price_selector)
        price_yen = parse_price_yen(price_raw, price_regex=source.price_regex)

        condition = _select_text(card, selectors.get("condition", "")) or source.default_condition
        stock_text = _select_text(card, selectors.get("stock", "")) or card.get_text(" ", strip=True)
        stock_status = _detect_stock_status(stock_text, source.stock_out_keywords)
        item_url = _select_link(card, selectors.get("link", ""), page_url)

        items.append(
            PriceItem(
                source_id=source.id,
                source_label=source.label,
                name_raw=name_raw,
                name_normalized=normalize_name(name_raw, config.normalization),
                condition=condition,
                price_yen=price_yen,
                stock_status=stock_status,
                url=item_url,
                fetched_at=fetched_at,
            )
        )

    next_url: str | None = None
    next_selector = selectors.get("next_page", "").strip()
    if next_selector:
        next_link = soup.select_one(next_selector)
        if next_link is not None and next_link.get("href"):
            href = str(next_link.get("href")).strip()
            if urlparse(page_url).scheme in {"http", "https"}:
                next_url = urljoin(page_url, href)
            else:
                next_url = str((Path(page_url).parent / href).as_posix())
    return items, next_url


def collect_html_list(
    source: SourceConfig,
    config: AppConfig,
    client: PoliteHttpClient,
    *,
    fetched_at: str,
) -> list[PriceItem]:
    start_urls = source.urls or ([source.url] if source.url else [])
    max_pages = min(
        source.max_pages or config.safety.max_pages_per_source,
        config.safety.max_pages_per_source,
    )
    all_items: list[PriceItem] = []
    visited: set[str] = set()
    pages_fetched = 0

    for start_url in start_urls:
        current_url: str | None = start_url
        while current_url and pages_fetched < max_pages:
            if current_url in visited:
                break
            visited.add(current_url)
            pages_fetched += 1
            html = client.fetch_text(current_url)
            page_items, next_url = _parse_html_list_page(
                html,
                source=source,
                config=config,
                page_url=current_url,
                fetched_at=fetched_at,
            )
            all_items.extend(page_items)
            current_url = next_url
    return all_items


def collect_html_single(
    source: SourceConfig,
    config: AppConfig,
    client: PoliteHttpClient,
    *,
    fetched_at: str,
) -> list[PriceItem]:
    target_urls = source.urls or ([source.url] if source.url else [])
    max_pages = min(
        source.max_pages or config.safety.max_pages_per_source,
        config.safety.max_pages_per_source,
    )
    selectors = source.selectors
    name_selector = selectors.get("name", "").strip()
    price_selector = selectors.get("price", "").strip()
    if not (name_selector and price_selector):
        raise ValueError(f"取得元 '{source.id}' (html_single) には selectors.name / price が必要です。")

    items: list[PriceItem] = []
    for target_url in target_urls[:max_pages]:
        html = client.fetch_text(target_url)
        soup = BeautifulSoup(html, "html.parser")
        name_raw = _select_text(soup, name_selector)
        if not name_raw:
            continue
        price_raw = _select_text(soup, price_selector)
        price_yen = parse_price_yen(price_raw, price_regex=source.price_regex)
        condition = _select_text(soup, selectors.get("condition", "")) or source.default_condition
        stock_text = _select_text(soup, selectors.get("stock", "")) or ""
        stock_status = _detect_stock_status(stock_text, source.stock_out_keywords) if stock_text else "available"
        items.append(
            PriceItem(
                source_id=source.id,
                source_label=source.label,
                name_raw=name_raw,
                name_normalized=normalize_name(name_raw, config.normalization),
                condition=condition,
                price_yen=price_yen,
                stock_status=stock_status,
                url=target_url,
                fetched_at=fetched_at,
            )
        )
    return items


def _iter_json_ld_products(payload: Any) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for entry in node:
                walk(entry)
            return
        if not isinstance(node, dict):
            return
        node_type = node.get("@type")
        type_list = node_type if isinstance(node_type, list) else [node_type]
        normalized_types = {str(t).lower() for t in type_list if t}
        if "product" in normalized_types:
            products.append(node)
            return
        if "itemlist" in normalized_types and isinstance(node.get("itemListElement"), list):
            for elem in node["itemListElement"]:
                if isinstance(elem, dict) and "item" in elem:
                    walk(elem["item"])
                else:
                    walk(elem)
            return
        if "@graph" in node:
            walk(node["@graph"])

    walk(payload)
    return products


def _extract_offer_price_and_stock(
    offers: Any, *, mode: str, stock_out_keywords: list[str]
) -> tuple[int | None, str, str]:
    offer_list = offers if isinstance(offers, list) else ([offers] if isinstance(offers, dict) else [])
    candidates: list[tuple[int, str, str]] = []
    fallback_stock = "available"
    fallback_url = ""

    for offer in offer_list:
        if not isinstance(offer, dict):
            continue
        availability = str(offer.get("availability", ""))
        stock_status = _detect_stock_status(availability, stock_out_keywords) if availability else "available"
        offer_url = str(offer.get("url", "")).strip()
        if offer_url and not fallback_url:
            fallback_url = offer_url
        if stock_status == "out_of_stock":
            fallback_stock = "out_of_stock"

        raw_price = offer.get("price")
        if raw_price is None:
            raw_price = offer.get("lowPrice") if mode == "lowest" else offer.get("highPrice")
        price_yen = parse_price_yen(raw_price)
        if price_yen is not None:
            candidates.append((price_yen, stock_status, offer_url))

    if not candidates:
        return None, fallback_stock, fallback_url

    # 在庫あり候補を優先し、比較モードに応じて最安または最高を選ぶ
    available_candidates = [c for c in candidates if c[1] != "out_of_stock"]
    pool = available_candidates or candidates
    chosen = min(pool, key=lambda c: c[0]) if mode == "lowest" else max(pool, key=lambda c: c[0])
    return chosen


def collect_json_ld(
    source: SourceConfig,
    config: AppConfig,
    client: PoliteHttpClient,
    *,
    fetched_at: str,
) -> list[PriceItem]:
    """Schema.org JSON-LD (<script type='application/ld+json'>) から商品価格を自動抽出する。"""
    target_urls = source.urls or ([source.url] if source.url else [])
    max_pages = min(
        source.max_pages or config.safety.max_pages_per_source,
        config.safety.max_pages_per_source,
    )
    items: list[PriceItem] = []

    for target_url in target_urls[:max_pages]:
        html = client.fetch_text(target_url)
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            raw_json = script.string or script.get_text()
            if not raw_json or not raw_json.strip():
                continue
            try:
                parsed = json.loads(raw_json)
            except json.JSONDecodeError:
                continue

            for product in _iter_json_ld_products(parsed):
                name_raw = str(product.get("name", "")).strip()
                if not name_raw:
                    continue
                price_yen, stock_status, offer_url = _extract_offer_price_and_stock(
                    product.get("offers"),
                    mode=config.project.comparison_mode,
                    stock_out_keywords=source.stock_out_keywords,
                )
                raw_cond = str(product.get("itemCondition", "")).strip()
                if "usedcondition" in raw_cond.lower():
                    condition = "中古"
                elif "newcondition" in raw_cond.lower():
                    condition = "新品"
                else:
                    condition = source.default_condition

                product_url = offer_url or str(product.get("url", "")).strip() or target_url
                if urlparse(target_url).scheme in {"http", "https"}:
                    product_url = urljoin(target_url, product_url)

                items.append(
                    PriceItem(
                        source_id=source.id,
                        source_label=source.label,
                        name_raw=name_raw,
                        name_normalized=normalize_name(name_raw, config.normalization),
                        condition=condition,
                        price_yen=price_yen,
                        stock_status=stock_status,
                        url=product_url,
                        fetched_at=fetched_at,
                    )
                )
    return items


def collect_csv_feed(
    source: SourceConfig,
    config: AppConfig,
    client: PoliteHttpClient,
    *,
    fetched_at: str,
) -> list[PriceItem]:
    """公開CSV（GoogleスプレッドシートCSV出力含む）から商品価格を読み込む。"""
    target_urls = source.urls or ([source.url] if source.url else [])
    col_map = source.columns
    name_col = col_map.get("name", "商品名")
    price_col = col_map.get("price", "価格")
    condition_col = col_map.get("condition", "状態")
    stock_col = col_map.get("stock", "在庫")
    url_col = col_map.get("url", "URL")

    items: list[PriceItem] = []
    for target_url in target_urls:
        csv_text = client.fetch_text(target_url)
        reader = csv.DictReader(io.StringIO(csv_text))
        for row in reader:
            name_raw = str(row.get(name_col) or "").strip()
            if not name_raw:
                continue
            price_yen = parse_price_yen(row.get(price_col), price_regex=source.price_regex)
            condition = str(row.get(condition_col) or "").strip() or source.default_condition
            stock_raw = str(row.get(stock_col) or "").strip()
            stock_status = _detect_stock_status(stock_raw, source.stock_out_keywords) if stock_raw else "available"
            item_url = str(row.get(url_col) or "").strip() or target_url

            items.append(
                PriceItem(
                    source_id=source.id,
                    source_label=source.label,
                    name_raw=name_raw,
                    name_normalized=normalize_name(name_raw, config.normalization),
                    condition=condition,
                    price_yen=price_yen,
                    stock_status=stock_status,
                    url=item_url,
                    fetched_at=fetched_at,
                )
            )
    return items


def collect_custom(
    source: SourceConfig,
    config: AppConfig,
    client: PoliteHttpClient,
    *,
    fetched_at: str,
) -> list[PriceItem]:
    """custom_collectors/<module>.py に配置したAI生成コレクターを読み込んで実行する。"""
    module_name = source.collector.strip()
    if module_name.endswith(".py"):
        module_name = module_name[:-3]
    if not VALID_COLLECTOR_NAME_RE.match(module_name):
        raise ValueError(
            f"取得元 '{source.id}' の collector 名が不正です: {source.collector!r}（半角英数字と _ のみ指定可能）"
        )

    collectors_dir = (config.config_dir / "custom_collectors").resolve()
    module_path = (collectors_dir / f"{module_name}.py").resolve()
    try:
        module_path.relative_to(collectors_dir)
    except ValueError as exc:
        raise ValueError(f"不正なコレクターパスです: {module_name}") from exc

    if not module_path.exists():
        raise FileNotFoundError(
            f"カスタムコレクターが見つかりません: {module_path}\n"
            "custom_collectors/ フォルダ内にファイルを配置してください。"
        )

    spec = importlib.util.spec_from_file_location(f"custom_collectors.{module_name}", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"カスタムコレクターを読み込めませんでした: {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    collect_fn = getattr(module, "collect", None)
    if not callable(collect_fn):
        raise AttributeError(
            f"{module_path.name} に collect(source, config, client, fetched_at) 関数が定義されていません。"
        )

    result = collect_fn(source=source, config=config, client=client, fetched_at=fetched_at)
    if not isinstance(result, list):
        raise TypeError(f"{module_path.name}.collect() は list[PriceItem] を返す必要があります。")
    for item in result:
        if not isinstance(item, PriceItem):
            raise TypeError(f"{module_path.name}.collect() の戻り値に PriceItem 以外が含まれています。")
        if not item.name_normalized:
            item.name_normalized = normalize_name(item.name_raw, config.normalization)
    return result


def collect_source(
    source: SourceConfig,
    config: AppConfig,
    client: PoliteHttpClient,
    *,
    fetched_at: str,
) -> list[PriceItem]:
    if source.type == "html_list":
        return collect_html_list(source, config, client, fetched_at=fetched_at)
    if source.type == "html_single":
        return collect_html_single(source, config, client, fetched_at=fetched_at)
    if source.type == "json_ld":
        return collect_json_ld(source, config, client, fetched_at=fetched_at)
    if source.type == "csv_feed":
        return collect_csv_feed(source, config, client, fetched_at=fetched_at)
    if source.type == "custom":
        return collect_custom(source, config, client, fetched_at=fetched_at)
    raise ValueError(f"未対応の取得タイプです: {source.type}")
