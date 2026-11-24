from __future__ import annotations

import sys
from pathlib import Path

TEMPLATE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TEMPLATE_ROOT / "src"))

from price_monitor.compare import build_comparison  # noqa: E402
from price_monitor.config import (  # noqa: E402
    AlertConfig,
    AlertTarget,
    AppConfig,
    NormalizationConfig,
    ProjectConfig,
    SafetyConfig,
    SourceConfig,
)
from price_monitor.models import PriceItem  # noqa: E402
from price_monitor.normalize import normalize_name, parse_price_yen  # noqa: E402


def test_parse_price_yen_handles_japanese_formats() -> None:
    assert parse_price_yen("¥44,800（税込）") == 44800
    assert parse_price_yen("４９，８００円") == 49800
    assert parse_price_yen("12800.00") == 12800
    assert parse_price_yen("要問い合わせ") is None
    assert parse_price_yen("0円") is None


def test_normalize_name_strips_phrases_and_resolves_alias() -> None:
    norm = NormalizationConfig(
        strip_phrases=["【新品・送料無料】", "【新品】", "税込"],
        strip_regex=[r"\([A-Z0-9-]+\)"],
        aliases={"sony wh1000xm5": "Sony WH-1000XM5"},
    )
    assert normalize_name("【新品・送料無料】ＳＯＮＹ　ＷＨ１０００ＸＭ５ (BLK) 税込", norm) == "Sony WH-1000XM5"


def _sample_items() -> list[PriceItem]:
    ts = "2026-11-24T17:00:00+09:00"
    return [
        PriceItem("a", "店舗A", "商品X", "商品X", "新品", 10000, "available", "https://a.example/x", ts),
        PriceItem("b", "店舗B", "商品X", "商品X", "新品", 12000, "available", "https://b.example/x", ts),
        PriceItem("a", "店舗A", "商品Y", "商品Y", "新品", 5000, "out_of_stock", "https://a.example/y", ts),
        PriceItem("b", "店舗B", "商品Y", "商品Y", "新品", 8000, "available", "https://b.example/y", ts),
    ]


def _make_config(mode: str, target_price: int) -> AppConfig:
    return AppConfig(
        project=ProjectConfig(title="テスト", comparison_mode=mode),
        safety=SafetyConfig(),
        normalization=NormalizationConfig(),
        alerts=AlertConfig(targets=[AlertTarget(item="商品X", target_price_yen=target_price, condition="新品")]),
        sources=[
            SourceConfig(id="a", label="店舗A", type="json_ld", url="https://a.example"),
            SourceConfig(id="b", label="店舗B", type="json_ld", url="https://b.example"),
        ],
        config_dir=TEMPLATE_ROOT,
    )


def test_comparison_lowest_mode_and_target_alert() -> None:
    cfg = _make_config("lowest", target_price=10500)
    compared, single, alerts = build_comparison(_sample_items(), cfg)

    assert len(compared) == 1
    assert compared[0].name_normalized == "商品X"
    assert compared[0].best_price_yen == 10000
    assert compared[0].best_sources == ["店舗A"]
    assert compared[0].spread_yen == 2000
    assert compared[0].target_hit is True

    # 商品Yは店舗Aが在庫切れのため店舗Bの単独掲載へ分離される
    assert len(single) == 1
    assert single[0].name_normalized == "商品Y"
    assert single[0].best_sources == ["店舗B"]

    assert len(alerts) == 1
    assert alerts[0].achieved is True
    assert alerts[0].diff_yen == -500


def test_comparison_highest_mode_for_buyback() -> None:
    cfg = _make_config("highest", target_price=11500)
    compared, single, alerts = build_comparison(_sample_items(), cfg)

    assert len(compared) == 1
    assert compared[0].best_price_yen == 12000
    assert compared[0].best_sources == ["店舗B"]
    assert compared[0].target_hit is True
    assert len(single) == 1
    assert alerts[0].achieved is True
    assert alerts[0].diff_yen == 500
