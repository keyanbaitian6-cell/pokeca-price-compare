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
    "ポケモンカード",
    "着払い対象外",
    "xy break",
    "xy",
)

# Longer phrases must be removed first so a short token cannot leave a suffix.
_SERIES_NAMES = (
    "スカーレット&バイオレット",
    "ダイヤモンド&パール",
    "ソード&シールド",
    "サン&ムーン",
)
_CONDITION_NAME_TOKENS = (
    "シュリンク付きボックス",
    "シュリンク付き",
    "シュリンク無し",
    "シュリンクなし",
    "シュリンク有り",
    "ペリペリ無し",
    "ぺりぺり無し",
    "シュリンク付",
    "シュリンク無",
    "シュリンク有",
    "ボックス",
    "box",
)
_SET_CODE_RE = re.compile(r"(?<![0-9A-Za-z])M\d+[A-Za-z]?(?![0-9A-Za-z])", re.IGNORECASE)
_PRODUCT_NAME_ALIASES = {
    # Collect omits the official trailing "ex" while the other stores retain it.
    "シャイニートレジャー": "シャイニートレジャーex",
}


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return _SPACE_RE.sub(" ", unicodedata.normalize("NFKC", value)).strip()


def parse_price(value: str | None) -> int | None:
    """Convert strings such as '¥17,500' to integer yen."""
    text = clean_text(value)
    if not text or text in {"-", "ASK", "ask"}:
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
    if "ぺりぺり無し" in normalized or "ぺりぺりなし" in normalized:
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
    )
    if any(marker in normalized for marker in box_markers):
        return "sealed_box"
    if "未開封" in normalized or "セット" in normalized or "カートン" in normalized:
        return "sealed_other"
    if any(marker in normalized for marker in ("シングル", "psa", "sar", "sr", "ar/chr")):
        return "single_card"
    return "unknown"


def normalize_product_name(name: str) -> str:
    """Build a cautious cross-store key while retaining set-specific words."""
    # Normalize before phrase removal so both ASCII '&' and full-width '＆' match.
    text = clean_text(unicodedata.normalize("NFKC", name)).casefold()
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
    text = re.sub(r"pokemon\s*card\s*game", "", text)
    for series_name in sorted(_SERIES_NAMES, key=len, reverse=True):
        text = text.replace(series_name.casefold(), " ")
    # Some stores write the series marker directly before Japanese text
    # (for example "MEGAドリームex"), where an ASCII word boundary does not match.
    text = re.sub(r"(?<![a-z])mega", "", text)
    text = re.sub(r"(?:強化)?拡張パック|ハイクラスパック", "", text)
    for token in sorted(_CONDITION_NAME_TOKENS, key=len, reverse=True):
        text = text.replace(token.casefold(), " ")
    # Parentheses are separators, not identity. After making them whitespace,
    # remove standalone store set codes such as M3, M5 and M1L.
    text = re.sub(r"[()（）]", " ", text)
    text = _SET_CODE_RE.sub(" ", text)
    text = text.translate(str.maketrans({"「": "", "」": "", "『": "", "』": "", "【": "", "】": ""}))
    text = re.sub(r"[^0-9a-zぁ-んァ-ヶ一-龠ー&]+", " ", text)
    normalized = _SPACE_RE.sub(" ", text).strip()
    return _PRODUCT_NAME_ALIASES.get(normalized, normalized)


def build_match_key(name: str, condition: str) -> tuple[str, str]:
    normalized_name = normalize_product_name(name)
    return normalized_name, f"{normalized_name}|{condition}"
