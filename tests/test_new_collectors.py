from __future__ import annotations

import json

import pandas as pd
import pytest

from card_price_compare.catalog import box_msrp_yen, box_series_label, lookup_box_metadata
from card_price_compare.collectors.homura import parse_homura_html
from card_price_compare.collectors.morimori import parse_morimori_html
from card_price_compare.collectors.rudeya import parse_rudeya_html
from card_price_compare.collectors.tcgpro import parse_tcgpro_html
from card_price_compare.compare import build_box_comparison, records_to_frame
from card_price_compare.normalize import classify_product_kind, normalize_product_name
from card_price_compare.prompt_builder import find_leaked_store_terms
from card_price_compare.stores import ALL_SOURCE_ORDER, DEFAULT_SOURCES, STORE_REGISTRY
from card_price_compare.web_export import build_web_market_payload


FETCHED_AT = "2026-11-27T17:00:00+09:00"


def test_parse_homura_html_extracts_shrink_and_no_shrink_without_splitting_nowrap() -> None:
    html = """
    <html><body>
      <p>価格最終更新 2026年11月27日 12:11</p>
      <table>
        <tr><th>画像</th><th>BOX</th><th>シュリンク有り</th><th>シュリンク無し</th></tr>
        <tr>
          <td>img</td>
          <td><span class="hmr-hublist__ttl">ハドウ<span style="white-space:nowrap">シーカー</span></span></td>
          <td><a class="hmr-hublist__price" href="/box/hado/">9,800円</a><span class="hmr-hub__fpg">減額ゼロ</span></td>
          <td><a class="hmr-hublist__price" href="/box/hado-ns/">7,200円</a></td>
        </tr>
        <tr>
          <td>img</td>
          <td><span class="hmr-hublist__ttl">ポケモンカード151</span>価格推移・当たりカード</td>
          <td><a class="hmr-hublist__price" href="/box/151/">42,000円</a></td>
          <td>-</td>
        </tr>
      </table>
    </body></html>
    """
    records = parse_homura_html(html, fetched_at=FETCHED_AT)
    assert len(records) == 3
    by_key = {r.match_key: r for r in records}
    assert by_key["ハドウシーカー|shrink_wrapped"].price_yen == 9_800
    assert by_key["ハドウシーカー|shrink_wrapped"].notes == "減額ゼロ対象"
    assert by_key["ハドウシーカー|shrink_wrapped"].source_updated_label == "2026年11月27日 12:11"
    assert by_key["ハドウシーカー|no_shrink"].price_yen == 7_200
    assert by_key["151|shrink_wrapped"].price_yen == 42_000


def test_parse_tcgpro_html_extracts_data_price_and_metadata() -> None:
    html = """
    <html><body>
      <div>2026年11月26日更新</div>
      <ul>
        <li class="kb-item" data-price="18500" data-q="メガドリームex M2a" data-cat="ハイクラスパック" data-date="20251128">
          <a class="kb-item__link" href="/box-kaitori/m2a/">MEGAドリームex</a>
        </li>
        <li class="kb-item" data-price="0" data-q="未発売BOX">
          <a class="kb-item__link" href="/box-kaitori/zero/">未発売</a>
        </li>
      </ul>
    </body></html>
    """
    records = parse_tcgpro_html(html, fetched_at=FETCHED_AT)
    assert len(records) == 1
    rec = records[0]
    assert rec.source == "tcgpro"
    assert rec.product_name_normalized == "ドリームex"
    assert rec.price_yen == 18_500
    assert rec.condition == "shrink_wrapped"
    assert rec.source_updated_label == "2026年11月26日"
    assert "発売日:2025-11-28" in rec.notes


def test_parse_morimori_html_excludes_cartons_and_psa() -> None:
    html = """
    <html><body>
      <p>2026年11月27日</p>
      <table>
        <tr><th>No</th><th>画像</th><th>シリーズ</th><th>種別</th><th>商品名</th><th>JAN</th><th>通常買取</th></tr>
        <tr>
          <td>1</td><td></td><td>SV</td><td>新品</td>
          <td><a href="/product/151">ポケモン\nポケモンカード151 BOX</a></td>
          <td>4521329346045</td><td>41,500円</td>
        </tr>
        <tr>
          <td>2</td><td></td><td>S&S</td><td>新品</td>
          <td><a href="/product/carton">ポケモン\nシャイニースターV carton</a></td>
          <td></td><td>2,000円</td>
        </tr>
        <tr>
          <td>3</td><td></td><td>SV</td><td>新品</td>
          <td><a href="/product/psa">ピカチュウ PSA10</a></td>
          <td></td><td>50,000円</td>
        </tr>
      </table>
      <table><tr><td>mobile duplicate</td></tr></table>
    </body></html>
    """
    records = parse_morimori_html(
        html,
        fetched_at=FETCHED_AT,
        page_url="https://www.morimori-kaitori.jp/category/price-list/2401001",
    )
    assert len(records) == 1
    assert records[0].product_name_normalized == "151"
    assert records[0].price_yen == 41_500
    assert records[0].condition == "shrink_wrapped"


def test_parse_rudeya_html_marks_stopped_items_as_out_of_stock() -> None:
    html = """
    <html><body>
      <p>2026年11月27日 19時03分現在</p>
      <article class="pgrid-card">
        <a class="product-card-name-link" href="/product/detail/100">ポケモンカードゲーム スカーレット&amp;バイオレット 強化拡張パック ポケモンカード151 BOX</a>
        <div class="product-card-price-value">43,000円</div>
        <div class="product-card-memo">新品未開封/シュリンク付きのみ</div>
        <div class="product-card-jan-text">JAN:4521329346045</div>
      </article>
      <article class="pgrid-card">
        <a class="product-card-name-link" href="/product/detail/101">ポケモンカードゲーム MEGA 拡張パック ハドウシーカー BOX</a>
        <div class="product-card-price-value">9,000円</div>
        <div class="product-card-memo">新品未開封/シュリンク付きのみ</div>
        <span class="product-card-stopped">お申込一時停止中</span>
      </article>
    </body></html>
    """
    records = parse_rudeya_html(html, fetched_at=FETCHED_AT)
    assert len(records) == 2
    by_name = {r.product_name_normalized: r for r in records}
    assert by_name["151"].stock_status == "active"
    assert by_name["151"].price_yen == 43_000
    assert by_name["ハドウシーカー"].stock_status == "out_of_stock"
    assert "お申込一時停止中" in by_name["ハドウシーカー"].notes

    # Stopped rudeya rows must be excluded from active comparison
    comp = build_box_comparison(records_to_frame(records))
    assert list(comp["product_name_normalized"]) == ["151"]


def test_normalize_and_catalog_cross_store_aliases() -> None:
    assert normalize_product_name("MEGAドリームex") == "ドリームex"
    assert normalize_product_name("メガドリームex [M2a]") == "ドリームex"
    assert normalize_product_name("25thアニバーサリーコレクション BOX") == "25th anniversary collection"
    assert normalize_product_name("キミを待つ島々 BOX") == "キミを待つ島々"
    assert normalize_product_name("SM1+ サン&ムーン") == "サン&ムーン"
    assert classify_product_kind("シャイニースターV carton") == "sealed_other"
    assert classify_product_kind("ポケモンカード151 カートン 12BOX") == "sealed_other"

    meta_151 = lookup_box_metadata("151")
    assert meta_151.series == "SV"
    assert meta_151.msrp_yen == 5_800
    assert box_series_label("テラスタルフェスex") == "SV"
    assert box_msrp_yen("テラスタルフェスex") == 5_500
    assert box_series_label("ニンジャスピナー") == "MEGA"
    assert box_msrp_yen("イーブイヒーローズ") == 4_950


def test_store_registry_and_multi_store_comparison_metrics() -> None:
    assert len(STORE_REGISTRY) == len(ALL_SOURCE_ORDER) == 7
    assert "collect" not in DEFAULT_SOURCES
    assert len(DEFAULT_SOURCES) == 6

    raw_df = pd.DataFrame(
        [
            {
                "source": src,
                "product_name_raw": "ポケモンカード151 BOX シュリンク付き",
                "product_name_normalized": "151",
                "match_key": "151|shrink_wrapped",
                "variant": "シュリンク有",
                "condition": "shrink_wrapped",
                "product_kind": "sealed_box",
                "price_yen": price,
                "price_min_yen": price,
                "price_max_yen": price,
                "stock_status": "active",
                "product_url": f"https://example.com/{src}",
                "source_updated_label": "",
                "fetched_at": FETCHED_AT,
                "notes": "",
            }
            for src, price in (
                ("homura", 44_000),
                ("tcgpro", 43_000),
                ("morimori", 42_000),
                ("runto", 40_000),
            )
        ]
        + [
            {
                "source": "homura",
                "product_name_raw": "151 シュリンク無",
                "product_name_normalized": "151",
                "match_key": "151|no_shrink",
                "variant": "シュリンク無し",
                "condition": "no_shrink",
                "product_kind": "sealed_box",
                "price_yen": 36_000,
                "price_min_yen": 36_000,
                "price_max_yen": 36_000,
                "stock_status": "active",
                "product_url": "https://example.com/homura-ns",
                "source_updated_label": "",
                "fetched_at": FETCHED_AT,
                "notes": "",
            }
        ]
    )

    comp = build_box_comparison(raw_df)
    shrink_row = comp[comp["condition"] == "shrink_wrapped"].iloc[0]
    assert shrink_row["matched_site_count"] == 4
    assert shrink_row["best_site"] == "homura"
    assert shrink_row["best_price_yen"] == 44_000
    assert shrink_row["lowest_price_yen"] == 40_000
    assert shrink_row["median_price_yen"] == 42_500
    assert shrink_row["second_best_price_yen"] == 43_000
    assert shrink_row["top_lead_yen"] == 1_000
    assert shrink_row["spread_yen"] == 4_000

    # Web export must aggregate cleanly and contain zero store terms
    trend = pd.DataFrame(
        [
            ["2026-11-20", "151", 41_000, "買取ホムラ"],
            ["2026-11-26", "151", 43_000, "トレカプロ"],
            ["2026-11-27", "151", 44_000, "買取ホムラ"],
        ],
        columns=["日付", "商品名", "最高値", "最高値の店"],
    )
    payload = build_web_market_payload(
        comp,
        trend,
        fetched_at=FETCHED_AT,
        active_store_count=4,
    )
    assert payload["schema_version"] == 2
    assert payload["anonymized"] is True
    assert payload["monitored_store_count"] == 4
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["high_yen"] == 44_000
    assert item["median_yen"] == 42_500
    assert item["low_yen"] == 40_000
    assert item["no_shrink_high_yen"] == 36_000
    assert item["no_shrink_gap_yen"] == 8_000
    assert item["prev_diff_yen"] == 1_000
    assert item["week_diff_yen"] == 3_000
    assert len(item["trend"]) == 3
    assert find_leaked_store_terms(json.dumps(payload, ensure_ascii=False)) == []


def test_web_market_payload_blocks_store_term_leakage() -> None:
    comp = pd.DataFrame(
        [
            {
                "product_name_normalized": "買取ホムラ特製BOX",
                "condition": "shrink_wrapped",
                "condition_inferred": False,
                "best_site": "homura",
                "best_price_yen": 10_000,
                "spread_yen": 0,
                "matched_site_count": 1,
            }
        ]
    )
    with pytest.raises(ValueError, match="特定店舗名"):
        build_web_market_payload(comp, fetched_at=FETCHED_AT)
