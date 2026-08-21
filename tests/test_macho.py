from types import SimpleNamespace

from card_price_compare.collectors.macho import (
    BUYBACK_PRICES_URL,
    fetch_macho_records,
    parse_macho_buyback_html,
)


MACHO_HTML = """
<div class="flex flex-col rounded-xl border-2">
  <span class="rounded">シュリンク有</span>
  <button class="line-clamp-2">ストームエメラルダ</button>
  <span class="font-mono font-black">¥ 17,600</span>
</div>
<div class="flex flex-col rounded-xl border-2">
  <span class="rounded">ペリ無</span><span>🧾 レシート同封必須</span>
  <button class="line-clamp-2">ストームエメラルダ</button>
  <span class="font-mono font-black">¥ 12,500</span>
</div>
<div class="flex flex-col rounded-xl border-2">
  <span class="rounded">パック</span>
  <button class="line-clamp-2">ストームエメラルダ</button>
  <span class="font-mono font-black">¥ 130</span>
</div>
<div class="flex flex-col rounded-xl border-2">
  <span class="rounded">統一パック</span>
  <button class="line-clamp-2">ストームエメラルダ</button>
  <span class="font-mono font-black">¥ 11,000</span>
</div>
<div class="flex flex-col rounded-xl border-2">
  <button class="line-clamp-2">タグ欠落パック</button>
  <span class="font-mono font-black">¥ 800</span>
</div>
"""


class _FakeRequester:
    def __init__(self) -> None:
        self.requested: list[str] = []

    def get(self, url: str, **_: object) -> SimpleNamespace:
        self.requested.append(url)
        return SimpleNamespace(text=MACHO_HTML, url=url)


def test_macho_cards_keep_box_conditions_and_exclude_pack_buyback() -> None:
    records = parse_macho_buyback_html(MACHO_HTML, fetched_at="2026-08-21T12:00:00+09:00")

    assert [record.price_yen for record in records] == [17_600, 12_500, 130, 11_000, 800]
    assert [record.condition for record in records] == [
        "shrink_wrapped",
        "no_perforation",
        "unspecified",
        "unspecified",
        "unspecified",
    ]
    assert [record.product_kind for record in records] == [
        "sealed_box",
        "sealed_box",
        "single_pack",
        "single_pack",
        "single_pack",
    ]
    assert records[1].notes == "レシート同封必須"
    assert records[0].match_key == "ストームエメラルダ|shrink_wrapped"


def test_macho_fetches_its_public_listing_once() -> None:
    requester = _FakeRequester()

    records = fetch_macho_records(requester, fetched_at="2026-08-21T12:00:00+09:00")

    assert requester.requested == [BUYBACK_PRICES_URL]
    assert len(records) == 5
