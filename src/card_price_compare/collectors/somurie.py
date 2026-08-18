from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin

from ..models import PriceRecord
from ..normalize import build_match_key, classify_product_kind, clean_text, detect_condition, parse_price


PRODUCTS_URL = "https://somurie-kaitori.com/products?category=2&subcategory=7"
OTHER_PRODUCTS_URL = "https://somurie-kaitori.com/products?category=2&subcategory=13"
PRODUCTS_URLS = (PRODUCTS_URL, OTHER_PRODUCTS_URL)


def parse_somurie_card_text(text: str, *, fetched_at: str, product_url: str = PRODUCTS_URL) -> PriceRecord:
    lines = [clean_text(line) for line in text.splitlines() if clean_text(line)]
    if not lines:
        raise ValueError("買取ソムリエの商品カードが空です。")
    name = lines[0]
    price: int | None = None
    price_index: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        if re.fullmatch(r"[\d,]+", line) and index + 1 < len(lines) and lines[index + 1] == "円":
            price = parse_price(line)
            price_index = index
            break
    # Defensive fallback for a rendered card whose block-level line breaks are
    # temporarily collapsed by the browser layout engine.
    if price is None:
        collapsed = clean_text(text)
        price_match = re.search(r"(?<!\d)(\d[\d,]*)\s*円", collapsed)
        if price_match:
            name = clean_text(collapsed[: price_match.start()])
            price = parse_price(price_match.group(1))
            price_index = None
    if price is None:
        raise ValueError(f"買取ソムリエの商品価格を解析できません: {name}")
    notes = " / ".join(lines[1:price_index]) if price_index else ""
    condition = detect_condition(f"{name} {notes}")
    normalized, key = build_match_key(name, condition)
    return PriceRecord(
        source="somurie",
        product_name_raw=name,
        product_name_normalized=normalized,
        match_key=key,
        variant="",
        condition=condition,
        product_kind=classify_product_kind(f"{name} {notes}"),
        price_yen=price,
        price_min_yen=price,
        price_max_yen=price,
        stock_status="active",
        product_url=product_url,
        source_updated_label="",
        fetched_at=fetched_at,
        notes=notes,
    )


def fetch_somurie_records(
    *,
    headless: bool = True,
    timeout_ms: int = 45_000,
    fetched_at: str | None = None,
) -> list[PriceRecord]:
    """Use Playwright because product cards are populated after JavaScript runs."""
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - depends on optional runtime setup
        raise RuntimeError(
            "Playwrightが未導入です。pip install -r requirements.txt と "
            "python -m playwright install chromium を実行してください。"
        ) from exc

    timestamp = fetched_at or datetime.now().astimezone().isoformat(timespec="seconds")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        page = browser.new_page(locale="ja-JP")
        try:
            records: list[PriceRecord] = []
            for products_url in PRODUCTS_URLS:
                page.goto(products_url, wait_until="domcontentloaded", timeout=timeout_ms)
                page.wait_for_function(
                    """() => document.querySelector('.ant-card') !== null ||
                    document.body.innerText.includes('商品が見つかりませんでした')""",
                    timeout=timeout_ms,
                )
                cards = page.locator(".ant-card")
                for index in range(cards.count()):
                    card = cards.nth(index)
                    # Read semantic paragraphs instead of relying on inner_text
                    # layout line breaks, which can briefly collapse into one line.
                    text = "\n".join(card.locator("p").all_inner_texts())
                    if "円" not in text:
                        continue
                    # The current cards have no detail-page anchor. Keep the
                    # category URL today, but automatically use an individual
                    # link if the site adds one later.
                    links = card.locator("a[href]")
                    href = links.first.get_attribute("href") if links.count() else None
                    product_url = urljoin(page.url, href) if href else products_url
                    records.append(
                        parse_somurie_card_text(
                            text,
                            fetched_at=timestamp,
                            product_url=product_url,
                        )
                    )
        except PlaywrightTimeoutError as exc:
            raise RuntimeError("買取ソムリエの商品一覧が時間内に表示されませんでした。") from exc
        finally:
            browser.close()

    if not records:
        raise RuntimeError("買取ソムリエから商品を1件も取得できませんでした。")
    return records
