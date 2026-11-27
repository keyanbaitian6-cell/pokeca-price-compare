from pathlib import Path

from card_price_compare.collectors.collect_sheet import parse_collect_html


def test_parse_collect_box_columns() -> None:
    html = Path("tests/fixtures/collect.html").read_text(encoding="utf-8")
    records = parse_collect_html(html, fetched_at="2026-08-18T00:00:00+09:00")
    boxes = [record for record in records if record.product_kind == "sealed_box"]
    assert len(boxes) == 3
    assert boxes[0].source_updated_label == "8月17日"
    assert boxes[0].price_yen == 17_500
    assert boxes[0].match_key == "ストームエメラルダ|shrink_wrapped"
    assert boxes[1].condition == "no_shrink"


def test_default_cli_sources_pause_collect() -> None:
    from card_price_compare.cli import build_parser
    from card_price_compare.stores import DEFAULT_SOURCES

    args = build_parser().parse_args([])
    parsed_sources = args.sources.split(",")
    assert parsed_sources == list(DEFAULT_SOURCES)
    assert "collect" not in parsed_sources
    assert set(parsed_sources) == {"homura", "tcgpro", "morimori", "runto", "rudeya", "somurie"}

