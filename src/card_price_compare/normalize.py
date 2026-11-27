from __future__ import annotations

import re
import unicodedata


_SPACE_RE = re.compile(r"\s+")
_PRICE_RE = re.compile(r"\d[\d,]*")

# Store- and era-specific boilerplate that is not part of the product identity.
# Longer phrases must be removed first (for example, ポケモンカードゲーム
# before ポケモンカード and XY BREAK before XY).
_PRODUCT_NAME_NOISE_TOKENS = (
    "ポケモンカードゲーム",
    "着払い対象外商品",
    "プロモカードなし",
    "ポケモンカード",
    "着払い対象外",
    "新品未開封",
    "xy break",
    "xy",
)

# Longer phrases must be removed first so a short token cannot leave a suffix.
# Allow optional spaces and optional '&' so variants like "ソード & シールド"
# and "ソード シールド" are removed alongside "ソード&シールド".
_SERIES_PATTERNS = (
    re.compile(r"スカーレット\s*&?\s*バイオレット", re.IGNORECASE),
    re.compile(r"ダイヤモンド\s*&?\s*パール", re.IGNORECASE),
    re.compile(r"ソード\s*&?\s*シールド", re.IGNORECASE),
    re.compile(r"サン\s*&?\s*ムーン", re.IGNORECASE),
    re.compile(r"(?<![0-9a-z])s\s*&\s*[vs](?![0-9a-z])", re.IGNORECASE),
)
_CONDITION_NAME_TOKENS = (
    "シュリンク付きボックス",
    "シュリンク付き",
    "シュリンク無し",
    "シュリンクなし",
    "シュリンク有り",
    "シュリンクあり",
    "シュリンクつき",
    "ペリペリ無し",
    "ぺりぺり無し",
    "ペリペリなし",
    "ぺりぺりなし",
    "シュリンク付",
    "シュリンク無",
    "シュリンク有",
    "ボックス",
    "box",
)
_SET_CODE_RE = re.compile(
    r"(?<![0-9A-Za-z_])(?:SV|SM|S|M|XY|BW|CP)\d+[A-Za-z]?(?:_DX)?(?![0-9A-Za-z_])",
    re.IGNORECASE,
)
_PRODUCT_NAME_ALIASES = {
    # Collect omits the official trailing "ex" while the other stores retain it.
    "シャイニートレジャー": "シャイニートレジャーex",
    "ポケモン go": "pokemon go",
    "ポケモンgo": "pokemon go",
    "ポケモンセンタートウホク": "スペシャル ポケモンセンタートウホク",
    "ポケモンセンターヒロシマ": "スペシャル ポケモンセンターヒロシマ",
    "ポケモンセンターフクオカ": "スペシャル ポケモンセンターフクオカ",
    "スペシャル トウホク": "スペシャル ポケモンセンタートウホク",
    "スペシャル ヒロシマ": "スペシャル ポケモンセンターヒロシマ",
    "スペシャル フクオカ": "スペシャル ポケモンセンターフクオカ",
    "デラックスブラックボルト": "ブラックボルト デラックス",
    "デラックスホワイトフレア": "ホワイトフレア デラックス",
    "デラックス ブラックボルト": "ブラックボルト デラックス",
    "デラックス ホワイトフレア": "ホワイトフレア デラックス",
    "ブラックボルトdx": "ブラックボルト デラックス",
    "ホワイトフレアdx": "ホワイトフレア デラックス",
    "メガドリームex": "ドリームex",
    "メガムニキスゼロ": "ムニキスゼロ",
    "25thアニバーサリー": "25th anniversary collection",
    "25thアニバーサリーコレクション": "25th anniversary collection",
    "ソードv": "ソード",
    "シールドv": "シールド",
    "30th celebration フューチャリスティック": "30th celebration futuristic",
    "コンセプトパックポケットモンスターカードゲーム 20th anniversary": (
        "コンセプトパック ポケットモンスターカードゲーム 20th anniversary"
    ),
    "ポケットモンスターカードゲーム 20th anniversary": (
        "コンセプトパック ポケットモンスターカードゲーム 20th anniversary"
    ),
}


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return _SPACE_RE.sub(" ", unicodedata.normalize("NFKC", value)).strip()


def parse_price(value: str | None) -> int | None:
    """Convert strings such as '¥17,500' to integer yen."""
    text = clean_text(value)
    if not text or text in {"-", "—", "―", "ASK", "ask"}:
        return None
    match = _PRICE_RE.search(text)
    return int(match.group(0).replace(",", "")) if match else None


def parse_price_range(value: str | None) -> tuple[int | None, int | None]:
    numbers = [int(part.replace(",", "")) for part in _PRICE_RE.findall(clean_text(value))]
    if not numbers:
        return None, None
    if len(numbers) == 1:
        return numbers[0], numbers[0]
    return min(numbers), max(numbers)


def detect_condition(text: str) -> str:
    normalized = clean_text(text).casefold()
    # Prefer the explicit product condition in phrases such as
    # "シュリンクなし ... ぺりぺりなし買取不可".
    if re.search(r"シュリンク\s*(なし|無し|無)", normalized):
        return "no_shrink"
    if "ぺりぺり無し" in normalized or "ぺりぺりなし" in normalized or "ペリペリ無し" in normalized or "ペリペリなし" in normalized:
        return "no_perforation"
    if re.search(r"シュリンク\s*(つき|付き|有|あり)", normalized):
        return "shrink_wrapped"
    if "未開封" in normalized or "外箱未開封" in normalized:
        return "sealed_unspecified"
    return "unspecified"


def classify_product_kind(text: str, *, force_box: bool = False) -> str:
    """Classify conservatively; only sealed_box rows enter the comparison table."""
    if force_box:
        return "sealed_box"
    normalized = clean_text(text).casefold()
    # Reject cartons and single-card/graded items before checking generic box markers
    # so listings like "ハイクラスパック シャイニースターV carton" never pollute BOX prices.
    if "カートン" in normalized or re.search(r"(?<![a-z])carton(?![a-z])", normalized):
        return "sealed_other"
    if any(marker in normalized for marker in ("シングル", "psa", "sar", "sr", "ar/chr")):
        return "single_card"
    non_box_markers = (
        "カードファイルセット",
        "スターターセット",
        "スタートデッキ",
        "プレミアムデッキセット",
        "スペシャルデッキセット",
        "デッキビルド",
        "カードセット",
        "アタッシュケース",
        "ポケモンセンターセット",
        "ポケセンセット",
    )
    if any(marker in normalized for marker in non_box_markers):
        return "sealed_other"
    condition = detect_condition(normalized)
    if condition in {"shrink_wrapped", "no_shrink", "no_perforation"}:
        return "sealed_box"
    box_markers = (
        "box",
        "ボックス",
        "拡張パック",
        "強化拡張パック",
        "ハイクラスパック",
        "未開封白箱",
        "ポケモンセンタートウホク",
        "ポケモンセンターヒロシマ",
        "ポケモンセンターフクオカ",
    )
    if any(marker in normalized for marker in box_markers):
        return "sealed_box"
    if "未開封" in normalized or "セット" in normalized:
        return "sealed_other"
    return "unknown"


def normalize_product_name(name: str) -> str:
    """Build a cautious cross-store key while retaining set-specific words."""
    # Normalize before phrase removal so both ASCII '&' and full-width '＆' match.
    text = clean_text(unicodedata.normalize("NFKC", name)).casefold()
    # Normalize accented Latin characters (e.g. Pokémon GO) without touching Japanese dakuten.
    text = text.replace("é", "e").replace("è", "e").replace("ê", "e")
    for token in sorted(_PRODUCT_NAME_NOISE_TOKENS, key=len, reverse=True):
        normalized_token = token.casefold()
        if re.fullmatch(r"[a-z ]+", normalized_token):
            # Keep short ASCII era markers such as XY from matching inside a word.
            text = re.sub(
                rf"(?<![0-9a-z]){re.escape(normalized_token)}(?![0-9a-z])",
                " ",
                text,
            )
        else:
            text = text.replace(normalized_token, " ")
    text = re.sub(r"pok[eé]mone?\s*card(?:\s*game)?", " ", text)
    # Remove pack-type prefixes before checking whether a series marker is the sole title
    # (for example SM1+ 強化拡張パック「サン&ムーン」 must remain "サン&ムーン").
    text = re.sub(
        r"(?:強化)?拡張パック|ハイクラスパック|プレミアムチャンピオンパック|コンセプトパック",
        " ",
        text,
    )
    for token in sorted(_CONDITION_NAME_TOKENS, key=len, reverse=True):
        text = text.replace(token.casefold(), " ")
    text = re.sub(r"[()（）\[\]]", " ", text)
    text = _SET_CODE_RE.sub(" ", text)
    text = text.translate(str.maketrans({"「": "", "」": "", "『": "", "』": "", "【": "", "】": ""}))
    for series_pattern in _SERIES_PATTERNS:
        candidate = series_pattern.sub(" ", text)
        if re.sub(r"[^0-9a-zぁ-んァ-ヶ一-龠々ー&×]+", "", candidate):
            text = candidate
    # Some stores write the series marker directly before Japanese text
    # (for example "MEGAドリームex"), where an ASCII word boundary does not match.
    text = re.sub(r"(?<![a-z])mega", "", text)
    text = re.sub(r"[^0-9a-zぁ-んァ-ヶ一-龠々ー&×]+", " ", text)
    normalized = _SPACE_RE.sub(" ", text).strip()
    return _PRODUCT_NAME_ALIASES.get(normalized, normalized)


def build_match_key(name: str, condition: str) -> tuple[str, str]:
    normalized_name = normalize_product_name(name)
    return normalized_name, f"{normalized_name}|{condition}"
