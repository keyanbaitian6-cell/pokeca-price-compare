from card_price_compare.collectors.somurie import parse_somurie_card_text


def test_parse_somurie_card() -> None:
    record = parse_somurie_card_text(
        """ポケモンカードゲーム アビスアイ （M5）シュリンク付き
        翌日必着
        8,800
        円
        最低買取数：1個
        ログインしてカートに追加""",
        fetched_at="2026-08-18T00:00:00+09:00",
    )
    assert record.price_yen == 8_800
    assert record.product_kind == "sealed_box"
    assert record.match_key == "アビスアイ|shrink_wrapped"


def test_explicit_no_shrink_beats_note_about_no_perforation() -> None:
    record = parse_somurie_card_text(
        """ポケモンカードゲーム ストームエメラルダ シュリンクなし
        切り込みはシュリンクなし扱い※ぺりぺりなし買取不可
        15,800
        円""",
        fetched_at="2026-08-18T00:00:00+09:00",
    )
    assert record.condition == "no_shrink"


def test_collapsed_card_text_still_parses_price() -> None:
    record = parse_somurie_card_text(
        "ポケモンカードゲーム ストームエメラルダ (M6)シュリンク付き17,500円最低買取数:1個",
        fetched_at="2026-08-18T00:00:00+09:00",
    )
    assert record.product_name_raw == "ポケモンカードゲーム ストームエメラルダ (M6)シュリンク付き"
    assert record.price_yen == 17_500
    assert record.match_key == "ストームエメラルダ|shrink_wrapped"
