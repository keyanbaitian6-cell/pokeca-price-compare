from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


MIN_SAFE_DELAY_SECONDS = 1.5
MAX_SAFE_PAGES_PER_SOURCE = 20
VALID_COMPARISON_MODES = frozenset({"lowest", "highest"})
VALID_SOURCE_TYPES = frozenset({"html_list", "html_single", "json_ld", "csv_feed", "custom"})
VALID_SOURCE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,40}$")


class ConfigError(ValueError):
    """config.json の構文・内容エラー。"""


@dataclass(slots=True)
class ProjectConfig:
    title: str = "マイ価格比較ダッシュボード"
    comparison_mode: str = "lowest"  # "lowest" (安く買う) | "highest" (高く売る)
    currency_symbol: str = "¥"
    spreadsheet_id: str = ""
    manual_update_url: str = ""


@dataclass(slots=True)
class SafetyConfig:
    request_delay_seconds: float = 2.0
    timeout_seconds: float = 20.0
    max_pages_per_source: int = 5
    respect_robots_txt: bool = True
    user_agent: str = "PersonalPriceMonitorKit/1.0 (+personal-low-frequency-use)"


@dataclass(slots=True)
class NormalizationConfig:
    strip_phrases: list[str] = field(default_factory=list)
    strip_regex: list[str] = field(default_factory=list)
    aliases: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class AlertTarget:
    item: str
    target_price_yen: int
    condition: str = ""


@dataclass(slots=True)
class AlertConfig:
    highlight_spread_rate: float = 0.05
    highlight_spread_yen: int = 3000
    targets: list[AlertTarget] = field(default_factory=list)


@dataclass(slots=True)
class NotificationConfig:
    enabled: bool = True
    notify_on_target_hit: bool = True
    notify_on_error: bool = True
    always_notify_summary: bool = False


@dataclass(slots=True)
class SourceConfig:
    id: str
    label: str
    type: str
    enabled: bool = True
    url: str = ""
    urls: list[str] = field(default_factory=list)
    default_condition: str = "標準"
    selectors: dict[str, str] = field(default_factory=dict)
    columns: dict[str, str] = field(default_factory=dict)
    price_regex: str = ""
    stock_out_keywords: list[str] = field(
        default_factory=lambda: ["売り切れ", "在庫なし", "在庫切れ", "品切れ", "SOLD OUT", "OutOfStock"]
    )
    max_pages: int | None = None
    collector: str = ""
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AppConfig:
    project: ProjectConfig
    safety: SafetyConfig
    normalization: NormalizationConfig
    alerts: AlertConfig
    sources: list[SourceConfig]
    config_dir: Path
    notifications: NotificationConfig = field(default_factory=NotificationConfig)

    @property
    def enabled_sources(self) -> list[SourceConfig]:
        return [source for source in self.sources if source.enabled]


def _validate_target_url(raw_url: str, *, source_id: str, config_dir: Path) -> None:
    url = raw_url.strip()
    if not url:
        raise ConfigError(f"取得元 '{source_id}' のURLが空です。")
    parsed = urlparse(url)
    if parsed.scheme:
        if parsed.scheme not in {"http", "https"}:
            raise ConfigError(
                f"取得元 '{source_id}' のURLスキーム '{parsed.scheme}' は利用できません。"
                "公開ページ（http:// または https://）か、プロジェクト内の相対パスを指定してください。"
            )
        if not parsed.netloc:
            raise ConfigError(f"取得元 '{source_id}' のURL '{url}' にホスト名がありません。")
        return
    # Local relative path (for offline demo / sample fixtures)
    candidate = (config_dir / url).resolve()
    try:
        candidate.relative_to(config_dir.resolve())
    except ValueError as exc:
        raise ConfigError(
            f"取得元 '{source_id}' のローカルパス '{url}' はプロジェクトフォルダ外を参照しています。"
        ) from exc


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path).resolve()
    if not config_path.exists():
        raise ConfigError(
            f"設定ファイルが見つかりません: {config_path}\n"
            "README.md を参考に config.json を配置してください。"
        )
    try:
        raw_data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"config.json のJSON書式に誤りがあります（{exc.lineno}行目・{exc.colno}列目付近）: {exc.msg}\n"
            "末尾の余分なカンマやダブルクォートの閉じ忘れを確認してください。"
        ) from exc

    if not isinstance(raw_data, dict):
        raise ConfigError("config.json の最上位はJSONオブジェクト（{ ... }）である必要があります。")

    project_raw = raw_data.get("project", {}) or {}
    comparison_mode = str(project_raw.get("comparison_mode", "lowest")).strip().lower()
    if comparison_mode not in VALID_COMPARISON_MODES:
        raise ConfigError(
            f"project.comparison_mode は 'lowest'（最安値比較）または 'highest'（最高値比較）を指定してください: {comparison_mode!r}"
        )
    project = ProjectConfig(
        title=str(project_raw.get("title", "マイ価格比較ダッシュボード")).strip() or "マイ価格比較ダッシュボード",
        comparison_mode=comparison_mode,
        currency_symbol=str(project_raw.get("currency_symbol", "¥")).strip() or "¥",
        spreadsheet_id=str(project_raw.get("spreadsheet_id", "")).strip(),
        manual_update_url=str(project_raw.get("manual_update_url", "")).strip(),
    )

    safety_raw = raw_data.get("safety", {}) or {}
    try:
        delay = float(safety_raw.get("request_delay_seconds", 2.0))
        timeout = float(safety_raw.get("timeout_seconds", 20.0))
        max_pages = int(safety_raw.get("max_pages_per_source", 5))
    except (TypeError, ValueError) as exc:
        raise ConfigError("safety の数値設定（request_delay_seconds / timeout_seconds / max_pages_per_source）が不正です。") from exc

    if delay < MIN_SAFE_DELAY_SECONDS:
        raise ConfigError(
            f"安全運用ガード: safety.request_delay_seconds は {MIN_SAFE_DELAY_SECONDS} 秒以上にしてください（現在: {delay}秒）。"
        )
    if timeout <= 0 or timeout > 120:
        raise ConfigError("safety.timeout_seconds は 1〜120 の範囲で指定してください。")
    if max_pages < 1 or max_pages > MAX_SAFE_PAGES_PER_SOURCE:
        raise ConfigError(
            f"安全運用ガード: safety.max_pages_per_source は 1〜{MAX_SAFE_PAGES_PER_SOURCE} の範囲で指定してください（現在: {max_pages}）。"
        )

    safety = SafetyConfig(
        request_delay_seconds=delay,
        timeout_seconds=timeout,
        max_pages_per_source=max_pages,
        respect_robots_txt=bool(safety_raw.get("respect_robots_txt", True)),
        user_agent=str(
            safety_raw.get("user_agent", "PersonalPriceMonitorKit/1.0 (+personal-low-frequency-use)")
        ).strip()
        or "PersonalPriceMonitorKit/1.0 (+personal-low-frequency-use)",
    )

    norm_raw = raw_data.get("normalization", {}) or {}
    strip_regex = [str(p) for p in norm_raw.get("strip_regex", []) if str(p)]
    for pattern in strip_regex:
        try:
            re.compile(pattern)
        except re.error as exc:
            raise ConfigError(f"normalization.strip_regex の正規表現が不正です ({pattern!r}): {exc}") from exc

    normalization = NormalizationConfig(
        strip_phrases=[str(p) for p in norm_raw.get("strip_phrases", []) if str(p)],
        strip_regex=strip_regex,
        aliases={str(k): str(v) for k, v in (norm_raw.get("aliases", {}) or {}).items()},
    )

    alerts_raw = raw_data.get("alerts", {}) or {}
    targets: list[AlertTarget] = []
    for index, target_raw in enumerate(alerts_raw.get("targets", []) or [], start=1):
        if not isinstance(target_raw, dict):
            raise ConfigError(f"alerts.targets[{index}] はオブジェクトで指定してください。")
        item_name = str(target_raw.get("item", "")).strip()
        if not item_name:
            raise ConfigError(f"alerts.targets[{index}].item が空です。")
        try:
            target_price = int(target_raw["target_price_yen"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ConfigError(f"alerts.targets[{index}].target_price_yen は整数で指定してください。") from exc
        if target_price <= 0:
            raise ConfigError(f"alerts.targets[{index}].target_price_yen は1円以上で指定してください。")
        targets.append(
            AlertTarget(
                item=item_name,
                target_price_yen=target_price,
                condition=str(target_raw.get("condition", "")).strip(),
            )
        )

    alerts = AlertConfig(
        highlight_spread_rate=float(alerts_raw.get("highlight_spread_rate", 0.05)),
        highlight_spread_yen=int(alerts_raw.get("highlight_spread_yen", 3000)),
        targets=targets,
    )

    sources_raw = raw_data.get("sources")
    if not isinstance(sources_raw, list) or not sources_raw:
        raise ConfigError("sources には1件以上の取得元サイトを設定してください。")

    sources: list[SourceConfig] = []
    seen_ids: set[str] = set()
    config_dir = config_path.parent
    for index, src_raw in enumerate(sources_raw, start=1):
        if not isinstance(src_raw, dict):
            raise ConfigError(f"sources[{index}] はオブジェクトで指定してください。")
        source_id = str(src_raw.get("id", "")).strip()
        if not VALID_SOURCE_ID_RE.match(source_id):
            raise ConfigError(
                f"sources[{index}].id は半角英数字・ハイフン・アンダースコア（1〜40文字）で指定してください: {source_id!r}"
            )
        if source_id in seen_ids:
            raise ConfigError(f"sources の id '{source_id}' が重複しています。")
        seen_ids.add(source_id)

        source_type = str(src_raw.get("type", "")).strip().lower()
        if source_type not in VALID_SOURCE_TYPES:
            raise ConfigError(
                f"取得元 '{source_id}' の type '{source_type}' は未対応です。"
                f"対応値: {', '.join(sorted(VALID_SOURCE_TYPES))}"
            )

        enabled = bool(src_raw.get("enabled", True))
        url = str(src_raw.get("url", "")).strip()
        urls = [str(u).strip() for u in (src_raw.get("urls", []) or []) if str(u).strip()]

        if enabled:
            if source_type == "html_single":
                target_urls = urls or ([url] if url else [])
                if not target_urls:
                    raise ConfigError(f"取得元 '{source_id}' (html_single) には urls または url を指定してください。")
                for u in target_urls:
                    _validate_target_url(u, source_id=source_id, config_dir=config_dir)
            elif source_type in {"html_list", "json_ld", "csv_feed"}:
                target_urls = urls or ([url] if url else [])
                if not target_urls:
                    raise ConfigError(f"取得元 '{source_id}' ({source_type}) には url を指定してください。")
                for u in target_urls:
                    _validate_target_url(u, source_id=source_id, config_dir=config_dir)
            elif source_type == "custom":
                collector_path = str(src_raw.get("collector", "")).strip()
                if not collector_path:
                    raise ConfigError(
                        f"取得元 '{source_id}' (custom) には collector（例: 'example_custom'）を指定してください。"
                    )
                if url:
                    _validate_target_url(url, source_id=source_id, config_dir=config_dir)
                for u in urls:
                    _validate_target_url(u, source_id=source_id, config_dir=config_dir)

        source_max_pages = src_raw.get("max_pages")
        if source_max_pages is not None:
            source_max_pages = int(source_max_pages)
            if source_max_pages < 1 or source_max_pages > MAX_SAFE_PAGES_PER_SOURCE:
                raise ConfigError(
                    f"取得元 '{source_id}' の max_pages は 1〜{MAX_SAFE_PAGES_PER_SOURCE} の範囲で指定してください。"
                )

        price_regex = str(src_raw.get("price_regex", "")).strip()
        if price_regex:
            try:
                re.compile(price_regex)
            except re.error as exc:
                raise ConfigError(f"取得元 '{source_id}' の price_regex が不正です: {exc}") from exc

        stock_out_raw = src_raw.get("stock_out_keywords")
        stock_out_keywords = (
            [str(k) for k in stock_out_raw if str(k)]
            if isinstance(stock_out_raw, list)
            else ["売り切れ", "在庫なし", "在庫切れ", "品切れ", "SOLD OUT", "OutOfStock"]
        )

        sources.append(
            SourceConfig(
                id=source_id,
                label=str(src_raw.get("label", source_id)).strip() or source_id,
                type=source_type,
                enabled=enabled,
                url=url,
                urls=urls,
                default_condition=str(src_raw.get("default_condition", "標準")).strip() or "標準",
                selectors={str(k): str(v) for k, v in (src_raw.get("selectors", {}) or {}).items()},
                columns={str(k): str(v) for k, v in (src_raw.get("columns", {}) or {}).items()},
                price_regex=price_regex,
                stock_out_keywords=stock_out_keywords,
                max_pages=source_max_pages,
                collector=str(src_raw.get("collector", "")).strip(),
                options=dict(src_raw.get("options", {}) or {}),
            )
        )

    if not any(source.enabled for source in sources):
        raise ConfigError("有効（enabled: true）な取得元サイトが1件もありません。")

    notif_raw = raw_data.get("notifications", {}) or {}
    if not isinstance(notif_raw, dict):
        raise ConfigError("notifications はJSONオブジェクト（{ ... }）で指定してください。")
    forbidden_secret_keys = {"webhook_url", "discord_webhook_url", "slack_webhook_url", "ntfy_topic_url", "token"}
    leaked_keys = sorted(forbidden_secret_keys.intersection({str(k).lower() for k in notif_raw}))
    if leaked_keys:
        raise ConfigError(
            f"安全運用ガード: 通知URLやトークン（{', '.join(leaked_keys)}）は config.json に書かず、"
            "GitHub Secrets（DISCORD_WEBHOOK_URL / SLACK_WEBHOOK_URL / NTFY_TOPIC_URL）へ登録してください。"
        )
    notifications = NotificationConfig(
        enabled=bool(notif_raw.get("enabled", True)),
        notify_on_target_hit=bool(notif_raw.get("notify_on_target_hit", True)),
        notify_on_error=bool(notif_raw.get("notify_on_error", True)),
        always_notify_summary=bool(notif_raw.get("always_notify_summary", False)),
    )

    return AppConfig(
        project=project,
        safety=safety,
        normalization=normalization,
        alerts=alerts,
        sources=sources,
        config_dir=config_dir,
        notifications=notifications,
    )
