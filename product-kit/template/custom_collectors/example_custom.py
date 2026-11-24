"""AI生成カスタムコレクターのひな形（動作確認済みサンプル）。

config.json で `"type": "custom"`, `"collector": "example_custom"` と指定すると
このファイルの `collect()` 関数が自動的に呼び出されます。
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from price_monitor.config import AppConfig, SourceConfig
from price_monitor.http_client import PoliteHttpClient
from price_monitor.models import PriceItem
from price_monitor.normalize import normalize_name, parse_price_yen


def collect(
    *,
    source: SourceConfig,
    config: AppConfig,
    client: PoliteHttpClient,
    fetched_at: str,
) -> list[PriceItem]:
    """独自構造のHTMLから価格レコードを抽出して返すサンプル関数。"""
    target_url = source.url or (source.urls[0] if source.urls else "")
    if not target_url:
        return []

    html = client.fetch_text(target_url)
    soup = BeautifulSoup(html, "html.parser")
    items: list[PriceItem] = []

    for row in soup.select("article.product-card"):
        title_node = row.select_one(".product-title")
        price_node = row.select_one(".product-price")
        if title_node is None or price_node is None:
            continue

        name_raw = title_node.get_text(" ", strip=True)
        price_yen = parse_price_yen(price_node.get_text(" ", strip=True))
        cond_node = row.select_one(".product-condition")
        condition = cond_node.get_text(" ", strip=True) if cond_node else source.default_condition
        badge = row.select_one(".stock-badge")
        badge_text = badge.get_text(" ", strip=True) if badge else ""
        stock_status = "out_of_stock" if any(k in badge_text for k in source.stock_out_keywords) else "available"
        link = row.select_one("a[href]")
        item_url = str(link["href"]) if link else target_url

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
                note="custom collector sample",
            )
        )
    return items
