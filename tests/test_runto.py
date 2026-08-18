import logging
from pathlib import Path
from types import SimpleNamespace

from card_price_compare.collectors.runto import (
    CATEGORY_URL,
    fetch_runto_records,
    parse_runto_product_html,
)


DETAIL_URL = "https://runto666.com/product/storm/"
LISTING_HTML = """
<ul>
  <li class="product product-type-variable">
    <a class="woocommerce-LoopProduct-link" href="/product/storm/"></a>
    <h2 class="woocommerce-loop-product__title">ポケモンカードゲーム MEGA 拡張パック「ストームエメラルダ」BOX</h2>
    <span class="price">15,800円 - 17,500円</span>
  </li>
</ul>
"""


class _FakeRequester:
    """Stand in for PoliteRequester so the test never touches the network."""

    def __init__(self, pages: dict[str, str]) -> None:
        self._pages = pages
        self.requested: list[str] = []

    def get(self, url: str, **_: object) -> SimpleNamespace:
        self.requested.append(url)
        return SimpleNamespace(text=self._pages[url], url=url)


def test_parse_runto_variations() -> None:
    html = Path("tests/fixtures/runto_product.html").read_text(encoding="utf-8")
    records = parse_runto_product_html(
        html,
        product_url="https://runto666.com/product/example/",
        fallback_name="fallback",
        stock_status="active",
        fetched_at="2026-08-18T00:00:00+09:00",
    )
    assert [record.price_yen for record in records] == [17_500, 15_800]
    assert [record.condition for record in records] == ["shrink_wrapped", "no_shrink"]
    assert records[0].match_key == "ストームエメラルダ|shrink_wrapped"


def test_listing_and_detail_progress_is_logged(caplog) -> None:
    """A polite one-request-per-second run stays silent for over a minute."""
    requester = _FakeRequester(
        {
            CATEGORY_URL: LISTING_HTML,
            DETAIL_URL: Path("tests/fixtures/runto_product.html").read_text(encoding="utf-8"),
        }
    )
    with caplog.at_level(logging.INFO, logger="card_price_compare.collectors.runto"):
        records = fetch_runto_records(requester, fetched_at="2026-08-18T00:00:00+09:00")

    assert requester.requested == [CATEGORY_URL, DETAIL_URL]
    assert len(records) == 2
    messages = [record.getMessage() for record in caplog.records]
    assert "runto: 一覧1ページ目 商品1件" in messages
    assert "runto: 商品詳細1件目 ポケモンカードゲーム MEGA 拡張パック「ストームエメラルダ」BOX" in messages
    assert "runto: 一覧1ページ・商品詳細1件から2件取得" in messages
