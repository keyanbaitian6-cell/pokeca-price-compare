from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .market_analysis import (
    MarketInsights,
    PriceMover,
    SpreadHighlight,
    analyze_market,
    solve_break_even_selling_price,
)


TOOL_SITE_BASE_URL = "https://keyanbaitian6-cell.github.io/pokeca-price-compare/"

# Default box selling assumptions aligned with site/js/calculators.js ITEM_TYPE_PRESETS.box.
DEFAULT_BOX_MERCARI_FEE_RATE = 0.10
DEFAULT_BOX_YAHOO_FEE_RATE = 0.05
DEFAULT_BOX_SHIPPING_YEN = 520
DEFAULT_BOX_PACKING_YEN = 120

from .stores import all_forbidden_store_terms

# Outward-facing prompts and drafts must never expose specific store identities
# or raw store-by-store price tables (see docs/DECISIONS.md).
FORBIDDEN_STORE_TERMS = all_forbidden_store_terms()

PROMPT_SHEET_HEADERS = [
    "区分",
    "タイトル",
    "おすすめ用途・タイミング",
    "コピペ用プロンプト／素材（そのままAIへ貼付）",
    "関連URL・収益導線メモ",
]


@dataclass(slots=True)
class PromptEntry:
    """One self-contained, copy-pasteable prompt or draft block."""

    entry_id: str
    category: str
    title: str
    timing_and_goal: str
    prompt_text: str
    target_url_and_monetization: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_sheet_row(self) -> list[str]:
        return [
            self.category,
            self.title,
            self.timing_and_goal,
            self.prompt_text,
            self.target_url_and_monetization,
        ]


@dataclass(slots=True)
class PromptBundle:
    """Full daily/weekly zero-API-cost AI prompt & draft package."""

    as_of_date: str
    fetched_at: str
    market_digest: str
    entries: list[PromptEntry]
    quick_x_drafts: dict[str, str]
    funnel_templates: dict[str, str]

    def get_entry(self, entry_id: str) -> PromptEntry:
        for entry in self.entries:
            if entry.entry_id == entry_id:
                return entry
        raise KeyError(f"Unknown prompt entry_id: {entry_id}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "as_of_date": self.as_of_date,
            "fetched_at": self.fetched_at,
            "market_digest": self.market_digest,
            "entries": [entry.to_dict() for entry in self.entries],
            "quick_x_drafts": dict(self.quick_x_drafts),
            "funnel_templates": dict(self.funnel_templates),
        }

    def to_sheet_rows(self) -> list[list[str]]:
        return [list(PROMPT_SHEET_HEADERS)] + [entry.to_sheet_row() for entry in self.entries]

    def to_markdown(self) -> str:
        lines = [
            f"# ポケカ未開封BOX 発信プロンプト＆下書き素材（{self.as_of_date} 更新）",
            "",
            f"- 計測基準日時（JST）: `{self.fetched_at}`",
            "- 使い方: 必要なブロックをコピーし、無料/Web版の ChatGPT・Gemini・Claude にそのまま貼り付けてください（APIキー課金不要）。",
            "- 安全設計: 特定店舗名および個別店舗の価格表生データは自動除外済みです。市場トレンド・値動き傾向・考察の素材としてご活用ください。",
            "",
        ]
        for entry in self.entries:
            lines.extend(
                [
                    f"## [{entry.category}] {entry.title}",
                    "",
                    f"- **おすすめ用途・タイミング**: {entry.timing_and_goal}",
                    f"- **関連URL・収益導線**: {entry.target_url_and_monetization}",
                    "",
                    "```text",
                    entry.prompt_text,
                    "```",
                    "",
                ]
            )
        return "\n".join(lines)


def build_tool_urls(base_url: str = TOOL_SITE_BASE_URL) -> dict[str, str]:
    normalized = base_url.rstrip("/") + "/"
    return {
        "top": normalized,
        "sell_compare": f"{normalized}sell-compare.html",
        "psa": f"{normalized}psa.html",
        "oripa": f"{normalized}oripa.html",
        "portfolio": f"{normalized}portfolio.html",
    }


def find_leaked_store_terms(text: str) -> list[str]:
    lowered = text.casefold()
    return [term for term in FORBIDDEN_STORE_TERMS if term.casefold() in lowered]


def _format_yen(amount: int | float) -> str:
    return f"{int(round(amount)):,}円"


def _format_signed_yen(amount: int) -> str:
    if amount > 0:
        return f"+{amount:,}円"
    if amount < 0:
        return f"{amount:,}円"
    return "±0円"


def _format_signed_pct(rate: float) -> str:
    pct = rate * 100
    if pct > 0:
        return f"+{pct:.1f}%"
    if pct < 0:
        return f"{pct:.1f}%"
    return "±0.0%"


def _format_pct(rate: float) -> str:
    return f"{rate * 100:.1f}%"


def _format_date_jp(iso_date: str) -> str:
    parts = iso_date.split("-")
    if len(parts) == 3:
        return f"{int(parts[0])}年{int(parts[1])}月{int(parts[2])}日"
    return iso_date


def _format_time_jst(fetched_at: str) -> str:
    if "T" in fetched_at:
        time_part = fetched_at.split("T", 1)[1]
        if len(time_part) >= 5:
            return f"{time_part[:5]} JST"
    return "最新"


def _format_movers_lines(movers: list[PriceMover], *, empty_message: str) -> str:
    if not movers:
        return f"- {empty_message}"
    lines: list[str] = []
    for rank, item in enumerate(movers, start=1):
        lines.append(
            f"{rank}. {item.product_name}：市場観測水準 {_format_yen(item.latest_price_yen)}"
            f"（{item.reference_date}比 {_format_signed_yen(item.diff_yen)} / {_format_signed_pct(item.diff_rate)}）"
        )
    return "\n".join(lines)


def _format_spread_lines(spreads: list[SpreadHighlight], *, empty_message: str) -> str:
    if not spreads:
        return f"- {empty_message}"
    lines: list[str] = []
    for rank, item in enumerate(spreads, start=1):
        lines.append(
            f"{rank}. {item.product_name}（{item.condition_label}）："
            f"店舗間最大差率 {_format_pct(item.spread_rate)} / 差額 {_format_yen(item.spread_yen)}"
            f"（観測価格帯 {_format_yen(item.lowest_price_yen)}〜{_format_yen(item.best_price_yen)}、"
            f"{item.compared_store_count}社比較・{item.highlight_reason}）"
        )
    return "\n".join(lines)


def _pick_representative_box_example(insights: MarketInsights) -> dict[str, Any]:
    """Select one concrete box and calculate exact break-even math matching トレカ損益ラボ."""
    if insights.combined_spread_highlights:
        picked = insights.combined_spread_highlights[0]
        name = picked.product_name
        buyback_yen = picked.best_price_yen
        context = (
            f"本日、複数買取店間の価格差が目立った注目BOX"
            f"（最大差率 {_format_pct(picked.spread_rate)} / 差額 {_format_yen(picked.spread_yen)}）"
        )
        is_sample_fallback = False
    elif insights.prev_gainers:
        picked_m = insights.prev_gainers[0]
        name = picked_m.product_name
        buyback_yen = picked_m.latest_price_yen
        context = (
            f"前回比で値上がりが目立ったBOX"
            f"（{_format_signed_yen(picked_m.diff_yen)} / {_format_signed_pct(picked_m.diff_rate)}）"
        )
        is_sample_fallback = False
    elif insights.week_gainers:
        picked_m = insights.week_gainers[0]
        name = picked_m.product_name
        buyback_yen = picked_m.latest_price_yen
        context = (
            f"7日前比で上昇傾向が目立ったBOX"
            f"（{_format_signed_yen(picked_m.diff_yen)} / {_format_signed_pct(picked_m.diff_rate)}）"
        )
        is_sample_fallback = False
    elif insights.prev_losers:
        picked_m = insights.prev_losers[0]
        name = picked_m.product_name
        buyback_yen = picked_m.latest_price_yen
        context = (
            f"前回比で値下がりが目立ったBOX"
            f"（{_format_signed_yen(picked_m.diff_yen)} / {_format_signed_pct(picked_m.diff_rate)}）"
        )
        is_sample_fallback = False
    else:
        name = "未開封BOX（相場12,000円モデル例）"
        buyback_yen = 12_000
        context = "未開封BOX1箱の一般的な相場帯シミュレーション例"
        is_sample_fallback = True

    fixed_costs = DEFAULT_BOX_SHIPPING_YEN + DEFAULT_BOX_PACKING_YEN
    mercari_be = solve_break_even_selling_price(
        buyback_yen, DEFAULT_BOX_MERCARI_FEE_RATE, fixed_costs
    )
    yahoo_be = solve_break_even_selling_price(
        buyback_yen, DEFAULT_BOX_YAHOO_FEE_RATE, fixed_costs
    )
    mercari_markup = mercari_be - buyback_yen
    mercari_markup_rate = round(mercari_markup / buyback_yen, 4) if buyback_yen > 0 else 0.0
    return {
        "product_name": name,
        "buyback_yen": buyback_yen,
        "context": context,
        "is_sample_fallback": is_sample_fallback,
        "fixed_costs_yen": fixed_costs,
        "mercari_break_even_yen": mercari_be,
        "yahoo_break_even_yen": yahoo_be,
        "mercari_markup_yen": mercari_markup,
        "mercari_markup_rate": mercari_markup_rate,
    }


def _compliance_rules_block() -> str:
    return "\n".join(
        [
            "【厳守ルール（安全・コンプライアンス）】",
            "- 特定の買取店舗名・店舗URL・個別店舗の価格表の生データ転載は一切行わないこと（本データは複数公開相場の集計値として店舗名を匿名化済み）。",
            "- 価格一覧の丸コピーではなく、値動きの傾向・背景仮説・売却や保管の意思決定に役立つ考察を中心に構成すること。",
            "- 「必ず上がる」「絶対に儲かる」等の断定表現・投資助言に該当する表現は避け、観測時点の事実と個人の考察として記述すること。",
            "- トレカ宅配買取・オンラインオリパ等のASPアフィリエイトリンクを案内する場合は、景品表示法（ステマ規制）に従い必ず「#PR」または「【PR】」を明記すること。",
            "- 収益導線は「無料計算ツール（トレカ損益ラボ）」「トレカ専門の宅配買取・オリパ等ASP」「note有料記事/メンバーシップ」に限定し、汎用モール系SNS紹介導線は含めないこと。",
        ]
    )


def _build_market_digest(insights: MarketInsights) -> str:
    s = insights.sentiment
    date_jp = _format_date_jp(insights.as_of_date)
    lines = [
        f"■ ポケカ未開封BOX（シュリンク有）市況ダイジェスト｜{date_jp} 時点",
        f"- 観測銘柄数：{insights.tracked_box_count}銘柄（うち複数店舗比較対象：{insights.multi_store_box_count}銘柄／蓄積履歴：{insights.history_days_available}日分）",
        f"- 相場全体の地合い：【{s.mood_label}】{s.mood_summary}",
    ]
    if insights.high_spread_box_count > 0 or insights.max_spread_yen:
        max_rate_str = _format_pct(insights.max_spread_rate) if insights.max_spread_rate is not None else "-"
        max_yen_str = _format_yen(insights.max_spread_yen) if insights.max_spread_yen is not None else "-"
        med_rate_str = _format_pct(insights.median_spread_rate) if insights.median_spread_rate is not None else "-"
        lines.append(
            f"- 店舗間価格差の広がり：注目基準（差率5%以上または差額3,000円以上）該当 {insights.high_spread_box_count}銘柄"
            f"（最大差率 {max_rate_str}／最大差額 {max_yen_str}／差率中央値 {med_rate_str}）"
        )
    lines.extend(
        [
            "",
            "【前回比 急上昇BOX】",
            _format_movers_lines(
                insights.prev_gainers,
                empty_message="該当なし（履歴2日目以降または上昇銘柄発生時に自動反映）",
            ),
            "",
            "【前回比 急落BOX】",
            _format_movers_lines(
                insights.prev_losers,
                empty_message="該当なし（履歴2日目以降または下落銘柄発生時に自動反映）",
            ),
            "",
            "【7日前比 急上昇BOX】",
            _format_movers_lines(
                insights.week_gainers,
                empty_message="該当なし（7日分以上の履歴蓄積後に自動反映）",
            ),
            "",
            "【7日前比 急落BOX】",
            _format_movers_lines(
                insights.week_losers,
                empty_message="該当なし（7日分以上の履歴蓄積後に自動反映）",
            ),
            "",
            "【店舗間価格差が大きい注目BOX（差率・差額ミックス／店舗名匿名）】",
            _format_spread_lines(
                insights.combined_spread_highlights,
                empty_message=(
                    f"本日は状態明記（シュリンク有確定）の比較で顕著な価格差BOXなし"
                    f"（状態推定の{insights.inferred_spread_excluded_count}件は精度優先で自動除外）"
                    if insights.inferred_spread_excluded_count > 0
                    else "本日は顕著な価格差BOXなし（または比較対象1店舗のみ）"
                ),
            ),
        ]
    )
    return "\n".join(lines)


def _build_x_breaking_prompt(insights: MarketInsights, urls: dict[str, str]) -> str:
    s = insights.sentiment
    date_jp = _format_date_jp(insights.as_of_date)
    time_label = _format_time_jst(insights.fetched_at)
    return "\n".join(
        [
            "あなたはポケモンカード未開封BOXの相場観測に詳しいX（旧Twitter）運用者です。",
            "以下の最新集計データ（店舗名匿名化済みの市場トレンド）をもとに、夕方〜夜に保存・インプレッションが伸びやすい「市況速報ポスト」を作成してください。",
            "",
            f"【最新データ（{date_jp} {time_label}更新）】",
            f"- 地合いサマリー：{s.mood_label}（{s.mood_summary}）",
            f"- 観測対象：シュリンク有未開封BOX {insights.tracked_box_count}銘柄（蓄積{insights.history_days_available}日分）",
            "",
            "■ 前回比 急上昇BOX：",
            _format_movers_lines(
                insights.prev_gainers[:3],
                empty_message="前回比上昇データ蓄積中（本日の市場観測水準と価格差トレンドを中心に速報化すること）",
            ),
            "",
            "■ 前回比 急落BOX：",
            _format_movers_lines(
                insights.prev_losers[:3],
                empty_message="前回比下落データなし（底堅い推移または履歴蓄積中として紹介すること）",
            ),
            "",
            "■ 7日前比の注目値動き：",
            "［上昇］",
            _format_movers_lines(
                insights.week_gainers[:2],
                empty_message="7日前比上昇データは履歴7日到達後に自動反映",
            ),
            "［下落］",
            _format_movers_lines(
                insights.week_losers[:2],
                empty_message="7日前比下落データは履歴7日到達後に自動反映",
            ),
            "",
            "【出力してほしいもの（3案）】",
            "1. 単発速報案（140文字以内・スマホで一目で読める箇条書き形式）",
            "2. 考察付き速報案（本文140文字以内で事実速報 → リプライ1つ目で「なぜ動いたか／売り時の見方」を補足）",
            "3. 保存狙いランキング案（改行を活かした視認性の高い構成＋「あとで見返す用に保存推奨」の自然な締め）",
            "",
            "【自然な導線設計（本文にはURLを入れず、リプライ欄に置く案を1つ添える）】",
            f"- 保有BOXの含み損益チェック導線：「トレカ損益ラボ｜BOX資産管理ポートフォリオ」 {urls['portfolio']}",
            "- 週次深掘りnoteへの予告：「週末のnoteで1週間の値動き背景と出口戦略をまとめています」",
            "- ハッシュタグは本文末尾に2個まで（例：#ポケカ #ポケカ相場）",
            "",
            _compliance_rules_block(),
        ]
    )


def _build_x_insight_prompt(
    insights: MarketInsights, urls: dict[str, str], rep: dict[str, Any]
) -> str:
    date_jp = _format_date_jp(insights.as_of_date)
    return "\n".join(
        [
            "あなたはトレカ売買の出口戦略（フリマと買取店の使い分け・手取り最大化）に詳しいX運用者です。",
            "以下の匿名化データをもとに、読者が「知らなかった！売る前に確認しよう」と保存・リポストしたくなる「気づき系ポスト」を作成してください。",
            "",
            f"【本日の店舗間価格差インサイト（{date_jp} 集計・店舗名匿名）】",
            f"- 複数店舗比較対象：{insights.multi_store_box_count}銘柄（うち差率5%以上または差額3,000円以上：{insights.high_spread_box_count}銘柄）",
            "",
            "■ 差率が大きい注目BOX：",
            _format_spread_lines(
                insights.spread_by_rate[:3],
                empty_message="本日は顕著な差率BOXなし（相場が均一化している点＋フリマ手数料の落とし穴をテーマにすること）",
            ),
            "",
            "■ 差額（円）が大きい注目BOX：",
            _format_spread_lines(
                insights.spread_by_yen[:3],
                empty_message="本日は顕著な差額BOXなし（高額BOXほど数％の差が数千円になる原則を解説すること）",
            ),
            "",
            "■ 参考：フリマ vs 買取の手取り逆転シミュレーション（トレカ損益ラボ同一計算式）",
            f"- 代表例：{rep['product_name']}（買取上限水準 {_format_yen(rep['buyback_yen'])} 前後）",
            f"- メルカリ（手数料10%＋宅急便コンパクト送料{DEFAULT_BOX_SHIPPING_YEN}円＋梱包{DEFAULT_BOX_PACKING_YEN}円）で買取手取りに勝つ出品ライン：{_format_yen(rep['mercari_break_even_yen'])} 以上（買取比 +{_format_yen(rep['mercari_markup_yen'])} / {_format_pct(rep['mercari_markup_rate'])} 上乗せが必要）",
            f"- Yahoo!フリマ（手数料5%・同諸費用）で勝つ出品ライン：{_format_yen(rep['yahoo_break_even_yen'])} 以上",
            "",
            "【出力してほしいもの（3案）】",
            "1. 「売る店の選び方だけで数千円変わる」気づきポスト（140文字以内・具体的な差率/差額の数字入り）",
            "2. 「高額BOXの落とし穴（差率が小さく見えても差額が大きい／フリマ10%手数料の壁）」解説ポスト（140文字以内）",
            "3. 権威性ポスト＋リプライ導線セット（リプライ1：無料ツール誘導、リプライ2：宅配買取ASP案内枠 ※必ず #PR を付与し『[ここに宅配買取ASPリンク]』プレースホルダを残す）",
            "",
            "【誘導先URL（リプライ欄配置を推奨）】",
            f"- フリマ vs 買取 手取り比較ツール：{urls['sell_compare']}",
            "- ハッシュタグは2個まで（例：#ポケカ #ポケモンカード）",
            "",
            _compliance_rules_block(),
        ]
    )


def _build_x_tool_funnel_prompt(
    insights: MarketInsights, urls: dict[str, str], rep: dict[str, Any]
) -> str:
    date_jp = _format_date_jp(insights.as_of_date)
    return "\n".join(
        [
            "あなたは無料Web計算ツール集『トレカ損益ラボ』の運営者兼ポケカコレクターです。",
            "売り込み感を一切出さず、「今日の相場で実際に計算してみたらこうだった」という実体験・検証トーンで、無料ツールへ自然に送客するXポストを3案作成してください。",
            "",
            f"【今日のネタ素材（{date_jp} 集計）】",
            f"- 注目銘柄：{rep['product_name']}（{rep['context']}）",
            f"- 市場観測の買取上限水準：{_format_yen(rep['buyback_yen'])} 前後",
            f"- メルカリ（10%手数料＋送料{DEFAULT_BOX_SHIPPING_YEN}円＋梱包{DEFAULT_BOX_PACKING_YEN}円）で手取り勝ちする最低出品額：{_format_yen(rep['mercari_break_even_yen'])}",
            f"- Yahoo!フリマ（5%手数料＋同諸費用）で手取り勝ちする最低出品額：{_format_yen(rep['yahoo_break_even_yen'])}",
            f"- 本日の地合い：{insights.sentiment.mood_label}（{insights.sentiment.mood_summary}）",
            "",
            "【送客先ツール一覧（用途に合うURLをリプライ1つ目に設置）】",
            f"- フリマ vs 買取店 手取り比較（最優先）：{urls['sell_compare']}",
            f"- 未開封BOX 資産管理＆利回りポートフォリオ：{urls['portfolio']}",
            f"- PSA鑑定 損益分岐点シミュレーター：{urls['psa']}",
            f"- オリパ還元率・爆死確率計算機：{urls['oripa']}",
            f"- トレカ損益ラボ トップ（総合ハブ）：{urls['top']}",
            "",
            "【出力してほしいもの（3パターン）】",
            "1. 『手取り逆転の衝撃』型（フリマ相場と買取水準の差を数字で見せ、リプライで sell-compare.html へ誘導）",
            "2. 『保有BOX棚卸し』型（本日の値動き地合いから「手元のBOXの含み益とメルカリ売却時の実手取りを把握しておくと迷わない」と語り、リプライで portfolio.html へ誘導）",
            "3. 『ツール開発者・実体験』型（「登録不要・スマホ10秒で計算できるように自作した無料ツール」として自然にトップページを紹介）",
            "",
            "【構成のコツ】",
            "- 本文は140文字以内、URLはXのインプレッション低下を防ぐため本文には入れず「↓無料ツールはリプ欄」でリプライ1つ目に貼る形式にする。",
            "- ハッシュタグは2個まで（例：#ポケカ #ポケカ投資 または #ポケモンカード）。",
            "- 誘導先ページ内には文脈連動の宅配買取・オリパ・サプライ案内が設置済みのため、X本文での過剰なセールスは不要。",
            "",
            _compliance_rules_block(),
        ]
    )


def _build_weekly_note_prompt(
    insights: MarketInsights, urls: dict[str, str], rep: dict[str, Any]
) -> str:
    s = insights.sentiment
    date_jp = _format_date_jp(insights.as_of_date)
    return "\n".join(
        [
            "あなたはポケモンカード未開封BOX市場を定点観測するnote執筆者（有料記事＆メンバーシップ運営）です。",
            "以下の週次集計データ（店舗名匿名化済み）をもとに、「無料パートで信頼と保存価値を作り、有料パートで“価格表の転載ではない独自の考察・出口戦略”に課金したくなる」週次note記事の構成案と本文ドラフトを作成してください。",
            "",
            f"【週次市場データ（基準日：{date_jp}／蓄積履歴：{insights.history_days_available}日分）】",
            f"- 観測銘柄数：シュリンク有未開封BOX {insights.tracked_box_count}銘柄（複数店舗比較：{insights.multi_store_box_count}銘柄）",
            f"- 地合いサマリー：{s.mood_label}（{s.mood_summary}）",
            f"- 店舗間価格差の注目銘柄数（差率5%以上または差額3,000円以上）：{insights.high_spread_box_count}銘柄",
            "",
            "■ 7日前比 急上昇BOX TOP5：",
            _format_movers_lines(
                insights.week_gainers,
                empty_message="7日分の履歴蓄積中（直近の前回比上昇データと市場全体の値動き傾向で補完すること）",
            ),
            "",
            "■ 7日前比 急落BOX TOP5：",
            _format_movers_lines(
                insights.week_losers,
                empty_message="7日分の履歴蓄積中（直近の前回比下落データとリスク管理視点で補完すること）",
            ),
            "",
            "■ 直近（前回比）急上昇・急落ピックアップ：",
            "［上昇］",
            _format_movers_lines(insights.prev_gainers[:3], empty_message="直近の上昇データなし"),
            "［下落］",
            _format_movers_lines(insights.prev_losers[:3], empty_message="直近の下落データなし"),
            "",
            "■ 店舗間価格差が大きい注目BOX（差率・差額ミックス／匿名）：",
            _format_spread_lines(
                insights.combined_spread_highlights,
                empty_message="今週は顕著な価格差BOXなし",
            ),
            "",
            "■ 代表BOXの売却損益分岐サンプル（トレカ損益ラボ基準）：",
            f"- {rep['product_name']}（買取水準 {_format_yen(rep['buyback_yen'])} 前後）→ メルカリ損益分岐 {_format_yen(rep['mercari_break_even_yen'])}／Yahoo!フリマ損益分岐 {_format_yen(rep['yahoo_break_even_yen'])}",
            "",
            "【記事の構成指定（合計 3,000〜4,500文字目安）】",
            "1. 記事タイトル案を5つ（検索・X流入を狙った具体数字入りタイトル）",
            "2. 【無料パート（全体の約35〜40%）】",
            "   - 今週のポケカ未開封BOX地合い総評（上昇vs下落バランスと相場の空気感）",
            "   - 今週もっとも印象的だった値動きBOX 1〜2銘柄のダイジェスト解説",
            "   - 相場が動いた週に損をしやすい「フリマ手数料10%＋送料の落とし穴」と無料ツール誘導：",
            f"     ・フリマ vs 買取 手取り比較：{urls['sell_compare']}",
            f"     ・未開封BOX 資産管理ポートフォリオ：{urls['portfolio']}",
            "   - 有料ライン直前の『読むメリット提示』（※「価格一覧が載っている」ではなく「値動きの背景仮説・売る/持つ判断フレームワーク・来週の監視ポイントが分かる」価値訴求にする）",
            "3. ──── ここから有料ライン（想定価格：単体300〜500円／メンバーシップ月額500〜980円読み放題） ────",
            "4. 【有料パート（全体の約60〜65%）】",
            "   - 7日前比 急上昇・急落BOXの詳細分析（なぜ動いたかのチェック観点：再販サイクル、絶版時期、封入トップレア相場、季節需要などを構造化して解説。著者の実体験・所感を追記しやすい `[著者メモ追記枠]` も2箇所入れる）",
            "   - 店舗間価格差が開くBOX帯の特徴と「宅配買取 vs フリマ vs 保有継続」の3択判断フローチャート",
            "   - 来週の注目イベント・再販警戒チェックリスト（読者がそのまま自分の行動に落とせる5項目）",
            f"   - 保有BOX棚卸しワーク（{urls['portfolio']} を使って含み益・利回りを見直す3ステップ）",
            "   - 結び＆メンバーシップ案内（継続購読のメリット＋次週予告）＋記事末尾のPR枠プレースホルダ（宅配買取・オンラインオリパASP用 ※【PR】表記必須）",
            "",
            _compliance_rules_block(),
        ]
    )


def _build_quick_x_drafts(
    insights: MarketInsights, urls: dict[str, str], rep: dict[str, Any]
) -> dict[str, str]:
    """Deterministic, ready-to-tweak fallback drafts for busy days without opening an LLM."""
    s = insights.sentiment
    short_date = insights.as_of_date[5:].replace("-", "/") if len(insights.as_of_date) >= 10 else insights.as_of_date

    # Draft 1: Breaking
    if insights.prev_gainers or insights.prev_losers:
        highlights: list[str] = []
        if insights.prev_gainers:
            g = insights.prev_gainers[0]
            highlights.append(
                f"📈 上昇注目：{g.product_name}（前回比 {_format_signed_yen(g.diff_yen)} / {_format_signed_pct(g.diff_rate)}）"
            )
        if insights.prev_losers:
            l = insights.prev_losers[0]
            highlights.append(
                f"📉 調整注目：{l.product_name}（前回比 {_format_signed_yen(l.diff_yen)} / {_format_signed_pct(l.diff_rate)}）"
            )
        breaking = (
            f"【{short_date} ポケカ未開封BOX市況メモ】\n"
            f"地合い：{s.mood_label}｜上昇{s.prev_up_count}・下落{s.prev_down_count}・横ばい{s.prev_flat_count}\n"
            + "\n".join(highlights)
            + "\n保有BOXの含み益チェックはリプ欄の無料ツールへ👇\n#ポケカ #ポケカ相場"
        )
    else:
        breaking = (
            f"【{short_date} ポケカ未開封BOX市況メモ】\n"
            f"本日シュリンク有BOX {insights.tracked_box_count}銘柄を定点観測。"
            f"店舗間で差率5%以上/差額3,000円以上の注目BOXは{insights.high_spread_box_count}銘柄でした。\n"
            "売る前の手取り比較はリプ欄の無料ツールで10秒計算👇\n#ポケカ #ポケカ相場"
        )

    # Draft 2: Insight
    if insights.combined_spread_highlights:
        sp = insights.combined_spread_highlights[0]
        insight = (
            f"同じ未開封BOXでも「売る先選び」で手取りはかなり変わります。\n"
            f"本日観測の「{sp.product_name}」は買取店間で最大{_format_pct(sp.spread_rate)}（差額{_format_yen(sp.spread_yen)}）の開きあり。\n"
            "フリマ出品前に手数料10%＋送料520円込みで手取り比較すると失敗しにくいです👇\n#ポケカ #ポケモンカード"
        )
    else:
        insight = (
            "ポケカ未開封BOXをメルカリで売る時、見落としがちなのがコストの壁。\n"
            f"手数料10%＋送料{DEFAULT_BOX_SHIPPING_YEN}円＋梱包{DEFAULT_BOX_PACKING_YEN}円で、"
            f"買取水準{_format_yen(rep['buyback_yen'])}に勝つには{_format_yen(rep['mercari_break_even_yen'])}以上の販売が必要です。\n"
            "損益分岐点の逆算ツールはリプ欄へ👇\n#ポケカ #ポケモンカード"
        )

    # Draft 3: Tool funnel
    tool_post = (
        f"「{rep['product_name']}」を例にフリマvs買取の手取りを計算してみた結果👇\n"
        f"買取水準{_format_yen(rep['buyback_yen'])}に対し、メルカリ（10%＋送料等）で手取り勝ちするには"
        f"{_format_yen(rep['mercari_break_even_yen'])}以上が必要（+{_format_yen(rep['mercari_markup_yen'])}の壁）。\n"
        "登録不要・10秒で逆算できる無料計算ツールはリプ欄に置きました！\n#ポケカ #ポケカ投資"
    )
    reply_cta = f"無料計算ツール「トレカ損益ラボ」はこちら👇\n・フリマ vs 買取 手取り比較：{urls['sell_compare']}\n・BOX資産管理ポートフォリオ：{urls['portfolio']}"

    return {
        "breaking": breaking,
        "insight": insight,
        "tool_funnel": tool_post,
        "reply_cta": reply_cta,
    }


def _build_funnel_templates(urls: dict[str, str], rep: dict[str, Any]) -> dict[str, str]:
    return {
        "x_reply_sell_compare": (
            f"▼ 10秒で逆算できる無料ツール（登録不要）\n"
            f"「トレカ損益ラボ｜フリマ vs 買取店 手取り比較」\n"
            f"{urls['sell_compare']}\n"
            f"メルカリ10%・Yahoo!フリマ5%・送料・梱包費を自動控除して損益分岐点が出ます。"
        ),
        "x_reply_portfolio": (
            f"▼ 保有BOXの含み損益・利回り管理はこちら（無料・ブラウザ保存）\n"
            f"「トレカ損益ラボ｜未開封BOX 資産管理ポートフォリオ」\n"
            f"{urls['portfolio']}"
        ),
        "x_reply_asp_pr": (
            "#PR フリマの出品・値下げ交渉・梱包の手間を省きたい場合は、トレカ専門の宅配買取でまとめて査定する選択肢もあります。\n"
            "▶ 査定・キャンペーン詳細：[ここにA8.net／もしもアフィリエイトの宅配買取リンクを貼付]\n"
            f"※ 事前にフリマとの手取り差を比べたい方はこちら（無料）：{urls['sell_compare']}"
        ),
        "x_pinned_post": (
            "ポケカ未開封BOXの市況トレンドと「損しない売り方・持ち方」を毎日定時で発信しています📊\n\n"
            "▼ 無料計算ツール集「トレカ損益ラボ」（登録不要・スマホ対応）\n"
            f"① フリマ vs 買取 手取り比較：{urls['sell_compare']}\n"
            f"② BOX資産＆利回り管理：{urls['portfolio']}\n"
            f"③ PSA鑑定 損益分岐点：{urls['psa']}\n"
            f"④ オリパ還元率・爆死確率：{urls['oripa']}\n\n"
            "▼ 週末の深掘り市況レポート（note）\n"
            "[ここにnoteプロフィール／メンバーシップURLを貼付]"
        ),
        "note_footer": (
            "---\n"
            "### ツール＆関連リンク\n"
            f"- **無料計算ツール「トレカ損益ラボ」**：{urls['top']}\n"
            f"  - フリマ vs 買取 手取り比較：{urls['sell_compare']}\n"
            f"  - 未開封BOX 資産ポートフォリオ：{urls['portfolio']}\n"
            "- **週次レポート読み放題（メンバーシップ）**：[ここにnoteメンバーシップURL]\n"
            "- **【PR】トレカ専門の宅配買取／オンラインオリパ**：[ここにASPリンク（掲載時は必ず【PR】表記を維持）]\n"
            f"- *参考計算例：{rep['product_name']}（買取水準 {_format_yen(rep['buyback_yen'])} → メルカリ損益分岐 {_format_yen(rep['mercari_break_even_yen'])}）*\n"
            "- *免責事項：本記事は複数公開相場の傾向をまとめた個人の考察であり、特定銘柄の売買や価格上昇を保証するものではありません。*"
        ),
    }


def _format_quick_drafts_block(drafts: dict[str, str]) -> str:
    return "\n\n".join(
        [
            "【① 速報系クイック下書き】\n" + drafts["breaking"],
            "【② 気づき系クイック下書き】\n" + drafts["insight"],
            "【③ ツール誘導系クイック下書き】\n" + drafts["tool_funnel"],
            "【共通リプライ欄（URL設置用）】\n" + drafts["reply_cta"],
        ]
    )


def _format_funnel_templates_block(templates: dict[str, str]) -> str:
    return "\n\n".join(
        [
            "【Xリプライ①：フリマ vs 買取ツール誘導】\n" + templates["x_reply_sell_compare"],
            "【Xリプライ②：BOX資産管理ツール誘導】\n" + templates["x_reply_portfolio"],
            "【Xリプライ③：宅配買取ASP導線（#PR必須）】\n" + templates["x_reply_asp_pr"],
            "【X固定ポスト用テンプレート】\n" + templates["x_pinned_post"],
            "【note記事末尾 共通フッター】\n" + templates["note_footer"],
        ]
    )


def build_prompt_bundle(
    insights: MarketInsights,
    *,
    tool_base_url: str = TOOL_SITE_BASE_URL,
) -> PromptBundle:
    """Build zero-API-cost, store-anonymized AI prompts and quick drafts from MarketInsights."""
    urls = build_tool_urls(tool_base_url)
    rep = _pick_representative_box_example(insights)

    market_digest = _build_market_digest(insights)
    x_breaking = _build_x_breaking_prompt(insights, urls)
    x_insight = _build_x_insight_prompt(insights, urls, rep)
    x_tool_funnel = _build_x_tool_funnel_prompt(insights, urls, rep)
    weekly_note = _build_weekly_note_prompt(insights, urls, rep)
    quick_drafts = _build_quick_x_drafts(insights, urls, rep)
    funnel_templates = _build_funnel_templates(urls, rep)

    entries = [
        PromptEntry(
            entry_id="market_digest",
            category="市況サマリー",
            title="本日の市況ダイジェスト（匿名集計データ）",
            timing_and_goal="毎日の自動更新直後：相場の全体感・注目銘柄の把握＆AIへの追加質問素材",
            prompt_text=market_digest,
            target_url_and_monetization=f"総合ハブ：{urls['top']}\n※店舗名・生価格表は自動除外済み",
        ),
        PromptEntry(
            entry_id="x_breaking",
            category="X投稿①",
            title="速報系プロンプト（急上昇・急落＆地合い）",
            timing_and_goal="毎日18:00〜21:00：定点観測アカウントの認知獲得・インプレッション＆保存狙い",
            prompt_text=x_breaking,
            target_url_and_monetization=(
                f"誘導先：{urls['portfolio']}\n収益導線：フォロワー獲得 → 週次note／BOX資産管理ツール"
            ),
        ),
        PromptEntry(
            entry_id="x_insight",
            category="X投稿②",
            title="気づき系プロンプト（店舗間価格差・売り方考察）",
            timing_and_goal="毎日朝7:30〜9:00または昼12:00：保存・リポスト増＆宅配買取ASPへの自然導線",
            prompt_text=x_insight,
            target_url_and_monetization=(
                f"誘導先：{urls['sell_compare']}\n収益導線：フリマvs買取ツール ＋ 宅配買取ASP（#PR必須）"
            ),
        ),
        PromptEntry(
            entry_id="x_tool_funnel",
            category="X投稿③",
            title="ツール誘導系プロンプト（トレカ損益ラボ送客）",
            timing_and_goal="週3〜5回：高購買意欲ユーザーを無料計算ツールへ送客し文脈連動ASPで成約",
            prompt_text=x_tool_funnel,
            target_url_and_monetization=(
                f"誘導先：{urls['sell_compare']} / {urls['top']}\n収益導線：ツール直下の宅配買取・オリパ・PSAサプライASP"
            ),
        ),
        PromptEntry(
            entry_id="weekly_note",
            category="週次note",
            title="週次note記事プロンプト（無料導入＋有料深掘り）",
            timing_and_goal="毎週末（金〜日曜）：note有料記事（300〜980円）＆メンバーシップ（月額500〜980円）",
            prompt_text=weekly_note,
            target_url_and_monetization=(
                f"誘導先：{urls['top']}\n収益導線：note有料記事・メンバーシップ ＋ ツール送客 ＋ ASP（【PR】表記）"
            ),
        ),
        PromptEntry(
            entry_id="quick_x_drafts",
            category="下書き素材",
            title="時短クイック下書きベース（30秒投稿用）",
            timing_and_goal="忙しい日：Web版AIを開く時間がない時でも数文字整えて即投稿できる素案",
            prompt_text=_format_quick_drafts_block(quick_drafts),
            target_url_and_monetization=(
                f"誘導先：{urls['sell_compare']}\n※リプライ欄にURLを分けて貼付推奨"
            ),
        ),
        PromptEntry(
            entry_id="funnel_templates",
            category="ツール導線",
            title="トレカ損益ラボ＆収益化 誘導テンプレート集",
            timing_and_goal="常設用：Xリプライ欄・固定ポスト・note末尾の共通フッターにコピペ",
            prompt_text=_format_funnel_templates_block(funnel_templates),
            target_url_and_monetization=(
                f"総合ハブ：{urls['top']}\n収益導線：ツール送客・宅配買取/オリパASP・noteメンバーシップ"
            ),
        ),
    ]

    return PromptBundle(
        as_of_date=insights.as_of_date,
        fetched_at=insights.fetched_at,
        market_digest=market_digest,
        entries=entries,
        quick_x_drafts=quick_drafts,
        funnel_templates=funnel_templates,
    )


def write_prompt_outputs(
    insights: MarketInsights,
    bundle: PromptBundle,
    output_dir: str | Path,
) -> dict[str, Path]:
    """Write local JSON & Markdown prompt artifacts into output_dir."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    insights_path = out / "market_insights.json"
    prompts_json_path = out / "ai_prompts.json"
    prompts_md_path = out / "ai_prompts.md"

    insights_path.write_text(
        json.dumps(insights.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    prompts_json_path.write_text(
        json.dumps(bundle.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    prompts_md_path.write_text(bundle.to_markdown(), encoding="utf-8")

    return {
        "market_insights": insights_path,
        "ai_prompts_json": prompts_json_path,
        "ai_prompts_md": prompts_md_path,
    }


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="保存済みの比較CSV・推移CSVから、API不要のX/note発信プロンプトを再生成します。"
    )
    parser.add_argument(
        "--comparison-csv",
        default="data/box_comparison.csv",
        help="build_box_comparison が出力した比較CSVのパス",
    )
    parser.add_argument(
        "--trend-csv",
        default="data/shrink_trend_history.csv",
        help="日次価格推移CSVのパス（任意）",
    )
    parser.add_argument("--output-dir", default="data", help="プロンプト出力先ディレクトリ")
    parser.add_argument("--top-n", type=int, default=5, help="ランキング抽出件数（既定: 5）")
    parser.add_argument(
        "--tool-url",
        default=TOOL_SITE_BASE_URL,
        help="誘導先の無料計算ツールURL（既定: トレカ損益ラボ GitHub Pages URL）",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_cli_parser().parse_args(argv)
    comp_path = Path(args.comparison_csv)
    trend_path = Path(args.trend_csv)

    comparison = pd.read_csv(comp_path, encoding="utf-8-sig") if comp_path.exists() else pd.DataFrame()
    trend_history = (
        pd.read_csv(trend_path, encoding="utf-8-sig") if trend_path.exists() else pd.DataFrame()
    )

    insights = analyze_market(comparison, trend_history, top_n=args.top_n)
    bundle = build_prompt_bundle(insights, tool_base_url=args.tool_url)
    paths = write_prompt_outputs(insights, bundle, args.output_dir)
    print(f"生成完了: {paths['ai_prompts_md']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
