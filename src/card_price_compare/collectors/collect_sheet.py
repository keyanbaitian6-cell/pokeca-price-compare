from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup

from ..http import PoliteRequester
from ..models import PriceRecord
from ..normalize import build_match_key, classify_product_kind, clean_text, detect_condition, parse_price


SPREADSHEET_ID = "1uNtzhQBeiPmGR8rjqgwNdesCHbD4Nr6Y4ecZAjBE15g"
POKEMON_SHEET_GID = "530894812"
PUBLIC_SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/htmlview"
PUBLIC_TABLE_URL = (
    f"https://docs.google.com/spreadsheets/u/0/d/{SPREADSHEET_ID}/"
    f"htmlview/sheet?headers=true&gid={POKEMON_SHEET_GID}"
)


def _data_cells(row: object) -> list[str]:
    cells = row.select("th, td")
    values = [clean_text(cell.get_text(" ", strip=True)) for cell in cells]
    # The HTML view adds the spreadsheet row number as the first cell.
    if cells and ("row-header" in " ".join(cells[0].get("class", [])) or values[0].isdigit()):
        values = values[1:]
    return values


def parse_collect_html(html: str, *, fetched_at: str) -> list[PriceRecord]:
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("table tr")
    if not rows:
        raise ValueError("コレクト価格表のtable要素が見つかりません。")

    parsed_rows = [_data_cells(row) for row in rows]
    update_label = ""
    for values in parsed_rows[:5]:
        match = re.search(r"\d{1,2}月\d{1,2}日", " ".join(values))
        if match:
            update_label = match.group(0)
            break

    header_index = next(
        (index for index, values in enumerate(parsed_rows) if values and values[0].upper() == "BOX"),
        None,
    )
    if header_index is None:
        raise ValueError("コレクト価格表のBOX見出しが見つかりません。")

    records: list[PriceRecord] = []
    for values in parsed_rows[header_index + 1 :]:
        values += [""] * (5 - len(values))
        box_name, wrapped_text, no_shrink_text, other_name, other_price_text = values[:5]

        # The left block is explicitly labeled BOX, so the product name alone may omit "BOX".
        if box_name:
            for variant, condition, raw_price in (
                ("シュリンクつき", "shrink_wrapped", wrapped_text),
                ("シュリンクなし", "no_shrink", no_shrink_text),
            ):
                price = parse_price(raw_price)
                if price is None:
                    continue
                normalized, key = build_match_key(box_name, condition)
                records.append(
                    PriceRecord(
                        source="collect",
                        product_name_raw=box_name,
                        product_name_normalized=normalized,
                        match_key=key,
                        variant=variant,
                        condition=condition,
                        product_kind="sealed_box",
                        price_yen=price,
                        price_min_yen=price,
                        price_max_yen=price,
                        stock_status="active",
                        product_url=PUBLIC_SHEET_URL,
                        source_updated_label=update_label,
                        fetched_at=fetched_at,
                    )
                )

        # The right block mixes boxes, sets, packs and single-card categories.
        other_price = parse_price(other_price_text)
        if other_name and other_price is not None:
            condition = detect_condition(other_name)
            normalized, key = build_match_key(other_name, condition)
            records.append(
                PriceRecord(
                    source="collect",
                    product_name_raw=other_name,
                    product_name_normalized=normalized,
                    match_key=key,
                    variant="",
                    condition=condition,
                    product_kind=classify_product_kind(other_name),
                    price_yen=other_price,
                    price_min_yen=other_price,
                    price_max_yen=other_price,
                    stock_status="active",
                    product_url=PUBLIC_SHEET_URL,
                    source_updated_label=update_label,
                    fetched_at=fetched_at,
                )
            )
    return records


def fetch_collect_records(requester: PoliteRequester, *, fetched_at: str | None = None) -> list[PriceRecord]:
    timestamp = fetched_at or datetime.now().astimezone().isoformat(timespec="seconds")
    response = requester.get(PUBLIC_TABLE_URL)
    response.encoding = response.apparent_encoding or "utf-8"
    return parse_collect_html(response.text, fetched_at=timestamp)

