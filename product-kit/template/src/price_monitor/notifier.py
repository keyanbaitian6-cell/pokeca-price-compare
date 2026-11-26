from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import requests

from .config import AppConfig
from .models import AlertRow, ComparisonRow


LOGGER = logging.getLogger(__name__)
SUPPORTED_WEBHOOK_SCHEMES = frozenset({"https"})


@dataclass(slots=True)
class NotificationResult:
    sent_channels: list[str]
    skipped_reason: str = ""
    errors: dict[str, str] | None = None


def _is_valid_https_url(url: str) -> bool:
    parsed = urlparse(url.strip())
    return parsed.scheme in SUPPORTED_WEBHOOK_SCHEMES and bool(parsed.netloc)


def build_notification_message(
    *,
    config: AppConfig,
    compared_rows: list[ComparisonRow],
    alert_rows: list[AlertRow],
    summary: dict[str, Any],
    sheet_url: str = "",
) -> tuple[str, str]:
    """スマホ通知向けの簡潔なタイトルと本文を組み立てる。"""
    mode = config.project.comparison_mode
    best_label = "最安値" if mode == "lowest" else "最高値"
    achieved = [row for row in alert_rows if row.achieved]
    errors = summary.get("errors") or {}

    if achieved:
        title = f"🎯 目標価格達成 ({len(achieved)}件) - {config.project.title}"
    elif errors:
        title = f"⚠️ 価格取得エラー ({len(errors)}件) - {config.project.title}"
    else:
        title = f"✅ 価格更新完了 - {config.project.title}"

    lines: list[str] = [
        f"【{config.project.title}】({summary.get('fetched_at', '')})",
        (
            f"全取得: {summary.get('record_count', 0)}件 / "
            f"比較対象: {summary.get('comparison_count', 0)}件 / "
            f"目標達成: {len(achieved)}件 / エラー: {len(errors)}件"
        ),
    ]

    if achieved:
        lines.append("")
        lines.append("■ 🎯 目標価格に到達した商品")
        for row in achieved[:8]:
            price_str = f"¥{row.current_best_yen:,}" if row.current_best_yen is not None else "-"
            lines.append(
                f"・{row.item_name} ({row.condition}): {best_label} {price_str} "
                f"[目標 ¥{row.target_price_yen:,} / {row.best_source_label}]"
            )
            if row.url and row.url.startswith(("http://", "https://")):
                lines.append(f"  {row.url}")
    elif compared_rows:
        lines.append("")
        lines.append("■ 価格差が大きい注目商品（上位3件）")
        for row in compared_rows[:3]:
            spread_str = f"¥{row.spread_yen:,}" if row.spread_yen is not None else "-"
            lines.append(
                f"・{row.name_normalized}: {best_label} ¥{row.best_price_yen:,} "
                f"[{row.best_source_label}] / 差額 {spread_str}"
            )

    if errors:
        lines.append("")
        lines.append("■ ⚠️ エラーが発生したサイト")
        for source_id, err_msg in list(errors.items())[:5]:
            lines.append(f"・{source_id}: {err_msg}")

    if sheet_url:
        lines.append("")
        lines.append(f"📊 スプレッドシート: {sheet_url}")

    return title, "\n".join(lines)


def should_send_notification(
    config: AppConfig,
    *,
    alert_rows: list[AlertRow],
    error_count: int,
    force_test: bool = False,
) -> tuple[bool, str]:
    if force_test:
        return True, ""
    notif = config.notifications
    if not notif.enabled:
        return False, "notifications.enabled が false です"
    has_hit = any(row.achieved for row in alert_rows)
    if notif.always_notify_summary:
        return True, ""
    if notif.notify_on_target_hit and has_hit:
        return True, ""
    if notif.notify_on_error and error_count > 0:
        return True, ""
    return False, "目標価格達成およびエラーがないため通知をスキップしました"


def send_notifications(
    *,
    config: AppConfig,
    compared_rows: list[ComparisonRow],
    alert_rows: list[AlertRow],
    summary: dict[str, Any],
    sheet_url: str = "",
    env: dict[str, str] | None = None,
    session: Any = None,
    force_test: bool = False,
) -> NotificationResult:
    """Discord / Slack / ntfy.sh へ無料プッシュ通知を送信する（有料API不要）。

    通知先URLは config.json ではなく環境変数（GitHub Secrets）からのみ読み込む。
      - DISCORD_WEBHOOK_URL : Discord Incoming Webhook URL
      - SLACK_WEBHOOK_URL   : Slack Incoming Webhook URL
      - NTFY_TOPIC_URL      : https://ntfy.sh/<推測されにくいトピック名>
    """
    runtime_env = os.environ if env is None else env
    discord_url = (runtime_env.get("DISCORD_WEBHOOK_URL") or "").strip()
    slack_url = (runtime_env.get("SLACK_WEBHOOK_URL") or "").strip()
    ntfy_url = (runtime_env.get("NTFY_TOPIC_URL") or "").strip()

    if not any((discord_url, slack_url, ntfy_url)):
        return NotificationResult(sent_channels=[], skipped_reason="通知先環境変数が未設定です")

    error_count = len(summary.get("errors") or {})
    do_send, reason = should_send_notification(
        config,
        alert_rows=alert_rows,
        error_count=error_count,
        force_test=force_test,
    )
    if not do_send:
        return NotificationResult(sent_channels=[], skipped_reason=reason)

    if force_test:
        title = f"🔔 通知テスト成功 - {config.project.title}"
        body = (
            f"【{config.project.title}】からのテスト通知です。\n"
            "このメッセージが届いていれば、目標価格達成時のスマホ自動通知は正常に動作します！"
        )
    else:
        title, body = build_notification_message(
            config=config,
            compared_rows=compared_rows,
            alert_rows=alert_rows,
            summary=summary,
            sheet_url=sheet_url,
        )

    http = session or requests
    sent: list[str] = []
    errors: dict[str, str] = {}

    if discord_url:
        if not _is_valid_https_url(discord_url):
            errors["discord"] = "DISCORD_WEBHOOK_URL は https:// 形式で指定してください"
        else:
            try:
                content = f"**{title}**\n{body}"[:1950]
                resp = http.post(discord_url, json={"content": content}, timeout=15)
                resp.raise_for_status()
                sent.append("discord")
            except Exception as exc:
                LOGGER.warning("Discord 通知送信に失敗しました: %s", exc)
                errors["discord"] = str(exc)

    if slack_url:
        if not _is_valid_https_url(slack_url):
            errors["slack"] = "SLACK_WEBHOOK_URL は https:// 形式で指定してください"
        else:
            try:
                resp = http.post(slack_url, json={"text": f"*{title}*\n{body}"[:3000]}, timeout=15)
                resp.raise_for_status()
                sent.append("slack")
            except Exception as exc:
                LOGGER.warning("Slack 通知送信に失敗しました: %s", exc)
                errors["slack"] = str(exc)

    if ntfy_url:
        if not _is_valid_https_url(ntfy_url):
            errors["ntfy"] = "NTFY_TOPIC_URL は https://ntfy.sh/... 形式で指定してください"
        else:
            try:
                headers = {
                    "Title": title.encode("ascii", "ignore").decode("ascii").strip() or "Price Monitor Alert",
                    "Priority": "high" if any(r.achieved for r in alert_rows) else "default",
                    "Tags": "bell,chart_with_upwards_trend",
                    "Content-Type": "text/plain; charset=utf-8",
                }
                resp = http.post(ntfy_url, data=f"{title}\n\n{body}".encode("utf-8"), headers=headers, timeout=15)
                resp.raise_for_status()
                sent.append("ntfy")
            except Exception as exc:
                LOGGER.warning("ntfy 通知送信に失敗しました: %s", exc)
                errors["ntfy"] = str(exc)

    return NotificationResult(sent_channels=sent, errors=errors or None)
