from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StoreInfo:
    """Metadata and buyback terms for one monitored buyback shop."""

    code: str
    label: str
    url: str
    default_enabled: bool
    shipping_rule: str
    price_lock_rule: str
    transfer_fee: str
    payout_speed: str
    no_shrink_supported: bool
    notes: str
    forbidden_terms: tuple[str, ...]


STORE_REGISTRY: tuple[StoreInfo, ...] = (
    StoreInfo(
        code="homura",
        label="買取ホムラ",
        url="https://kaitori-homura.com/column/2026/10/21/pokemon-box-buyback-price-list/",
        default_enabled=True,
        shipping_rule="5BOX以上で着払い無料（未満は元払い）",
        price_lock_rule="予約承認当日の集荷発送で価格保証",
        transfer_fee="10万円以上無料（未満200円）",
        payout_speed="トレカのみ即金振込（通常5〜7営業日）",
        no_shrink_supported=True,
        notes="対象シュリンク有BOXは減額ゼロ保証。シュリンク無も毎日更新。",
        forbidden_terms=("homura", "kaitori-homura", "買取ホムラ", "ホムラ"),
    ),
    StoreInfo(
        code="tcgpro",
        label="トレカプロ",
        url="https://tcgpro.co.jp/box-kaitori/",
        default_enabled=True,
        shipping_rule="5BOX以上で着払い可（未満は元払い）",
        price_lock_rule="申込から7日以内の到着で見積額保証",
        transfer_fee="無料（当社負担）",
        payout_speed="成立後 最短当日〜原則5営業日以内",
        no_shrink_supported=False,
        notes="MEGA〜BWまで115種を網羅。原則減額なし・初回住民票原本同封。",
        forbidden_terms=("tcgpro", "トレカプロ"),
    ),
    StoreInfo(
        code="morimori",
        label="森森買取",
        url="https://www.morimori-kaitori.jp/category/price-list/2401",
        default_enabled=True,
        shipping_rule="原則元払い（条件達成で着払い可）",
        price_lock_rule="査定承認後の承諾時点で価格保証",
        transfer_fee="銀行振込無料（現金書留は1,000円）",
        payout_speed="案内メール後2〜5営業日（即フリ0.5%）",
        no_shrink_supported=False,
        notes="現行SV/MEGAの高額帯に強い大手。通常買取価格を基準に表示。",
        forbidden_terms=("morimori", "森森買取", "森森"),
    ),
    StoreInfo(
        code="runto",
        label="runto",
        url="https://runto666.com/product-category/card/",
        default_enabled=True,
        shipping_rule="元払い（連絡なし着払いは受取拒否）",
        price_lock_rule="予約翌日午前着まで保証（遠方は翌々日午前）",
        transfer_fee="無料（当社負担）",
        payout_speed="検品完了後3〜5営業日以内",
        no_shrink_supported=True,
        notes="シュリンク有/無/ぺりぺり無＋旧裏まで網羅。返品送料無料CPあり。",
        forbidden_terms=("runto", "runto666", "ラントゥ"),
    ),
    StoreInfo(
        code="rudeya",
        label="買取ルデヤ",
        url="https://kaitori-rudeya.com/category/detail/114",
        default_enabled=True,
        shipping_rule="元払い（着払い不可）",
        price_lock_rule="当日発送・翌日午前着で価格保証",
        transfer_fee="振込手数料は条件により変動",
        payout_speed="到着後 翌営業日〜7営業日",
        no_shrink_supported=False,
        notes="新弾の即日掲載が速い。受付一時停止中の商品は比較対象から自動除外。",
        forbidden_terms=("rudeya", "kaitori-rudeya", "買取ルデヤ", "ルデヤ"),
    ),
    StoreInfo(
        code="somurie",
        label="買取ソムリエ",
        url="https://somurie-kaitori.com/products?category=2&subcategory=7",
        default_enabled=True,
        shipping_rule="公式条件を確認（元払い基準）",
        price_lock_rule="申込時の価格で買取（期限内到着）",
        transfer_fee="公式条件を確認",
        payout_speed="到着後5営業日以内",
        no_shrink_supported=False,
        notes="掲載数は少数精鋭だが、最新弾・注目弾で最高値が出やすい。",
        forbidden_terms=("somurie", "somurie-kaitori", "買取ソムリエ", "ソムリエ"),
    ),
    StoreInfo(
        code="collect",
        label="コレクト",
        url="https://docs.google.com/spreadsheets/d/1uNtzhQBeiPmGR8rjqgwNdesCHbD4Nr6Y4ecZAjBE15g/htmlview",
        default_enabled=False,
        shipping_rule="公式案内（X）を確認",
        price_lock_rule="公式案内（X）を確認",
        transfer_fee="公式案内（X）を確認",
        payout_speed="公式案内（X）を確認",
        no_shrink_supported=True,
        notes="スプレッドシート更新停止に伴い既定取得を一時中断中（--sources collect で手動再開可）。",
        forbidden_terms=("コレクト", "collect_sheet", "collect_tendo"),
    ),
)

STORE_BY_CODE: dict[str, StoreInfo] = {store.code: store for store in STORE_REGISTRY}
ALL_SOURCE_ORDER: tuple[str, ...] = tuple(store.code for store in STORE_REGISTRY)
DEFAULT_SOURCES: tuple[str, ...] = tuple(
    store.code for store in STORE_REGISTRY if store.default_enabled
)
SOURCE_LABELS: dict[str, str] = {store.code: store.label for store in STORE_REGISTRY}


def all_forbidden_store_terms() -> tuple[str, ...]:
    """Return every store name/domain token that must never leak to public outputs."""
    terms: list[str] = []
    seen: set[str] = set()
    for store in STORE_REGISTRY:
        for token in store.forbidden_terms:
            lowered = token.casefold()
            if lowered not in seen:
                seen.add(lowered)
                terms.append(token)
    return tuple(terms)
