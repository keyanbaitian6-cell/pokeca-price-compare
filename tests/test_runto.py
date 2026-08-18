from pathlib import Path

from card_price_compare.collectors.runto import parse_runto_product_html


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

