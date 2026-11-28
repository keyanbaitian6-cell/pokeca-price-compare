from __future__ import annotations

import sys
from pathlib import Path

import pytest

TEMPLATE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TEMPLATE_ROOT / "src"))

from price_monitor.config import SourceConfig, load_config  # noqa: E402
from price_monitor.http_client import PoliteHttpClient  # noqa: E402
from price_monitor.parsers import collect_source  # noqa: E402


FETCHED_AT = "2026-11-24T17:00:00+09:00"


def test_html_list_parser_extracts_items_and_stock() -> None:
    cfg = load_config(TEMPLATE_ROOT / "config.json")
    client = PoliteHttpClient(cfg.safety, base_dir=cfg.config_dir)
    source_beta = next(s for s in cfg.sources if s.id == "shop_beta")

    items = collect_source(source_beta, cfg, client, fetched_at=FETCHED_AT)
    assert len(items) == 5

    by_raw = {item.name_raw: item for item in items}
    airpods = by_raw["Apple AirPods Pro 第2世代 USB-C"]
    assert airpods.stock_status == "out_of_stock"
    assert airpods.price_yen == 33900

    sony = by_raw["【特価】SONY WH1000XM5 ワイヤレスヘッドホン 税込"]
    assert sony.name_normalized == "Sony WH-1000XM5 ワイヤレスヘッドホン"
    assert sony.price_yen == 41200
    assert sony.stock_status == "available"


def test_html_single_parser() -> None:
    cfg = load_config(TEMPLATE_ROOT / "config.examples" / "sneaker_oshi_watch.json")
    cfg.config_dir = TEMPLATE_ROOT
    client = PoliteHttpClient(cfg.safety, base_dir=TEMPLATE_ROOT)
    items = collect_source(cfg.sources[0], cfg, client, fetched_at=FETCHED_AT)
    assert len(items) == 1
    assert items[0].name_normalized == "推し活アクリルスタンド 限定Ver."
    assert items[0].price_yen == 3980
    assert items[0].stock_status == "available"


def test_json_ld_parser() -> None:
    cfg = load_config(TEMPLATE_ROOT / "config.json")
    client = PoliteHttpClient(cfg.safety, base_dir=cfg.config_dir)
    source_gamma = next(s for s in cfg.sources if s.id == "shop_gamma")

    items = collect_source(source_gamma, cfg, client, fetched_at=FETCHED_AT)
    assert len(items) == 2
    assert items[0].name_normalized == "Sony WH-1000XM5 ワイヤレスヘッドホン"
    assert items[0].price_yen == 42900
    assert items[0].condition == "新品"


def test_csv_feed_parser() -> None:
    cfg = load_config(TEMPLATE_ROOT / "config.json")
    client = PoliteHttpClient(cfg.safety, base_dir=cfg.config_dir)
    source_delta = next(s for s in cfg.sources if s.id == "shop_delta")

    items = collect_source(source_delta, cfg, client, fetched_at=FETCHED_AT)
    assert len(items) == 3
    assert items[0].price_yen == 35500

    limited = SourceConfig(
        id="csv_limited",
        label="CSV上限テスト",
        type="csv_feed",
        urls=[
            "sample_pages/shop_delta_feed.csv",
            "sample_pages/shop_delta_feed.csv",
            "sample_pages/shop_delta_feed.csv",
        ],
        columns=source_delta.columns,
        max_pages=2,
    )
    limited_items = collect_source(limited, cfg, client, fetched_at=FETCHED_AT)
    assert len(limited_items) == 6


def test_custom_collector_plugin_and_security() -> None:
    cfg = load_config(TEMPLATE_ROOT / "config.json")
    client = PoliteHttpClient(cfg.safety, base_dir=cfg.config_dir)

    custom_source = SourceConfig(
        id="custom_demo",
        label="カスタムデモ",
        type="custom",
        url="sample_pages/shop_alpha_electronics.html",
        collector="example_custom",
    )
    items = collect_source(custom_source, cfg, client, fetched_at=FETCHED_AT)
    assert len(items) == 5
    assert items[0].note == "custom collector sample"

    bad_source = SourceConfig(
        id="bad_custom",
        label="不正パス",
        type="custom",
        url="sample_pages/shop_alpha_electronics.html",
        collector="../evil",
    )
    with pytest.raises(ValueError, match="collector 名が不正"):
        collect_source(bad_source, cfg, client, fetched_at=FETCHED_AT)
