from __future__ import annotations

import re
import unicodedata

from .config import NormalizationConfig


DEFAULT_PRICE_RE = re.compile(r"(?:¥|￥)?\s*(\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\s*円?")
MULTISPACE_RE = re.compile(r"\s+")
EDGE_PUNCT_RE = re.compile(r"^[\s\-_/|・:：\[\]【】()（）]+|[\s\-_/|・:：\[\]【】()（）]+$")


def parse_price_yen(raw_text: str | int | float | None, *, price_regex: str = "") -> int | None:
    """価格文字列（例: '¥49,800（税込）' / '４９，８００円'）から整数円を抽出する。"""
    if raw_text is None:
        return None
    if isinstance(raw_text, bool):
        return None
    if isinstance(raw_text, (int, float)):
        value = int(round(raw_text))
        return value if value > 0 else None

    normalized = unicodedata.normalize("NFKC", str(raw_text)).strip()
    if not normalized:
        return None

    pattern = re.compile(price_regex) if price_regex else DEFAULT_PRICE_RE
    match = pattern.search(normalized)
    if not match:
        return None

    digits = match.group(1) if match.lastindex else match.group(0)
    digits = re.sub(r"[^\d]", "", digits)
    if not digits:
        return None
    value = int(digits)
    return value if value > 0 else None


def normalize_name(raw_name: str, norm_config: NormalizationConfig) -> str:
    """表記揺れを吸収し、複数サイトで同じ商品を比較できるように正規化する。"""
    text = unicodedata.normalize("NFKC", str(raw_name or "")).strip()
    if not text:
        return ""

    # 長いフレーズから順に除去して部分一致の削りすぎを防ぐ
    sorted_phrases = sorted(
        (unicodedata.normalize("NFKC", phrase) for phrase in norm_config.strip_phrases if phrase),
        key=len,
        reverse=True,
    )
    for phrase in sorted_phrases:
        text = text.replace(phrase, " ")

    for pattern in norm_config.strip_regex:
        text = re.sub(pattern, " ", text)

    text = MULTISPACE_RE.sub(" ", text).strip()
    text = EDGE_PUNCT_RE.sub("", text).strip()
    text = MULTISPACE_RE.sub(" ", text).strip()

    if not text:
        return ""

    # 別名辞書（大文字・小文字および全角・半角の揺れを吸収して照合）
    alias_lookup = {
        MULTISPACE_RE.sub(" ", unicodedata.normalize("NFKC", key)).strip().lower(): unicodedata.normalize(
            "NFKC", value
        ).strip()
        for key, value in norm_config.aliases.items()
    }
    return alias_lookup.get(text.lower(), text)
