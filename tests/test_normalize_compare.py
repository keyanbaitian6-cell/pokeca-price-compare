from card_price_compare.compare import build_box_comparison, records_to_frame
from card_price_compare.models import PriceRecord
from card_price_compare.normalize import build_match_key, normalize_product_name


def _record(source: str, name: str, condition: str, price: int) -> PriceRecord:
    normalized, key = build_match_key(name, condition)
    return PriceRecord(
        source=source,
        product_name_raw=name,
        product_name_normalized=normalized,
        match_key=key,
        variant="",
        condition=condition,
        product_kind="sealed_box",
        price_yen=price,
        price_min_yen=price,
        price_max_yen=price,
        stock_status="active",
        product_url="https://example.com",
        source_updated_label="",
        fetched_at="2026-08-18T00:00:00+09:00",
    )


def test_names_match_across_stores_and_best_price_is_selected() -> None:
    records = [
        _record("collect", "ストームエメラルダ", "shrink_wrapped", 17_500),
        _record(
            "runto",
            "ポケモンカードゲーム MEGA 拡張パック「ストームエメラルダ」",
            "shrink_wrapped",
            17_000,
        ),
        _record(
            "somurie",
            "ポケモンカードゲーム ストームエメラルダ （M6）シュリンク付きボックス",
            "shrink_wrapped",
            18_000,
        ),
    ]
    comparison = build_box_comparison(records_to_frame(records))
    assert len(comparison) == 1
    row = comparison.iloc[0]
    assert row["matched_site_count"] == 3
    assert row["best_site"] == "somurie"
    assert row["best_price_yen"] == 18_000
    assert row["spread_yen"] == 1_000
    assert str(comparison["collect_price_yen"].dtype) == "Int64"


def test_mega_prefix_attached_to_japanese_is_removed() -> None:
    assert normalize_product_name("MEGAドリームex") == "ドリームex"
    assert normalize_product_name("ハイクラスパック「MEGAドリームex」") == "ドリームex"


def test_series_names_full_width_ampersand_state_words_and_set_codes_are_removed() -> None:
    assert (
        normalize_product_name(
            "ポケモンカードゲーム スカーレット＆バイオレット 拡張パック 「クリムゾンヘイズ」"
        )
        == "クリムゾンヘイズ"
    )
    assert normalize_product_name("アビスアイ (M5)シュリンク付き") == "アビスアイ"
    assert normalize_product_name("ムニキスゼロ（M1L）シュリンク付きボックス") == "ムニキスゼロ"
    assert normalize_product_name("シャイニートレジャー") == "シャイニートレジャーex"


def test_pokemon_card_prefix_and_other_noise_are_removed_without_over_merging() -> None:
    assert normalize_product_name("ポケモンカード151") == "151"
    assert (
        normalize_product_name(
            "ポケモンカードゲーム スカーレット&バイオレット 強化拡張パック「151」"
        )
        == "151"
    )
    assert (
        normalize_product_name("ポケモンカードゲーム ポケモンカード151 カードファイルセット")
        == "151 カードファイルセット"
    )
    assert normalize_product_name("ポケモンカードe 基本 海からの風") == "e 基本 海からの風"
    assert (
        normalize_product_name("XY BREAK スペシャル レックウザポンチョを着たピカチュウ")
        == "スペシャル レックウザポンチョを着たピカチュウ"
    )
    assert (
        normalize_product_name("スタートデッキ100 未開封白箱 着払い対象外商品")
        == "スタートデッキ100 未開封白箱"
    )


def test_unspecified_condition_is_merged_and_flagged_as_inferred() -> None:
    records = [
        _record("collect", "白銀のランス", "shrink_wrapped", 17_000),
        _record(
            "runto",
            "ポケモンカードゲーム ソード&シールド 拡張パック 「白銀のランス」",
            "unspecified",
            17_500,
        ),
    ]
    comparison = build_box_comparison(records_to_frame(records))
    assert len(comparison) == 1
    assert comparison.iloc[0]["condition"] == "shrink_wrapped"
    assert bool(comparison.iloc[0]["condition_inferred"]) is True
    assert comparison.iloc[0]["matched_site_count"] == 2


def test_unspecified_condition_can_fill_both_real_condition_rows_without_merging_them() -> None:
    records = [
        _record("collect", "ステラミラクル", "shrink_wrapped", 11_000),
        _record("collect", "ステラミラクル", "no_shrink", 8_000),
        _record(
            "runto",
            "ポケモンカードゲーム スカーレット&バイオレット 強化拡張パック 「ステラミラクル」",
            "unspecified",
            11_800,
        ),
    ]
    comparison = build_box_comparison(records_to_frame(records))
    assert len(comparison) == 2
    assert set(comparison["condition"]) == {"shrink_wrapped", "no_shrink"}
    assert comparison["condition_inferred"].all()
    assert set(comparison["matched_site_count"]) == {2}


def test_no_perforation_remains_a_separate_comparable_condition() -> None:
    comparison = build_box_comparison(
        records_to_frame([_record("runto", "アビスアイ", "no_perforation", 5_800)])
    )
    assert len(comparison) == 1
    assert comparison.iloc[0]["condition"] == "no_perforation"
    assert comparison.iloc[0]["matched_site_count"] == 1


def test_sv_s_sm_set_codes_series_spacing_and_store_aliases_align() -> None:
    from card_price_compare.normalize import classify_product_kind

    assert (
        normalize_product_name("ポケモンカードゲーム テラスタルフェスex （SV8a）シュリンク付きボックス")
        == "テラスタルフェスex"
    )
    assert normalize_product_name("ハイクラスパック VSTARユニバース (S12a)") == "vstarユニバース"
    assert normalize_product_name("タッグオールスターズ SM12a") == "タッグオールスターズ"
    assert (
        normalize_product_name("ポケモンカードゲーム ソード & シールド 拡張パック ロストアビス")
        == "ロストアビス"
    )
    assert (
        normalize_product_name("ポケモンカードゲーム ソード シールド パラダイムトリガー")
        == "パラダイムトリガー"
    )
    assert normalize_product_name("強化拡張パック ポケモン GO") == "pokemon go"
    assert (
        normalize_product_name("ポケモンセンタートウホク")
        == normalize_product_name("スペシャルBOX ポケモンセンタートウホク")
        == "スペシャル ポケモンセンタートウホク"
    )
    assert (
        normalize_product_name("デラックスホワイトフレア")
        == normalize_product_name("拡張パックデラックス「ホワイトフレア」")
        == "ホワイトフレア デラックス"
    )
    assert classify_product_kind("ポケモンセンタートウホク") == "sealed_box"

