from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

TEMPLATE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TEMPLATE_ROOT / "src"))

from price_monitor.cli import build_markdown_summary, main  # noqa: E402
from price_monitor.config import ConfigError, load_config  # noqa: E402
from price_monitor.models import AlertRow, ComparisonRow  # noqa: E402
from price_monitor.notifier import send_notifications  # noqa: E402


def test_config_blocks_secret_webhook_url_inside_json(tmp_path: Path) -> None:
    bad = {
        "project": {"title": "テスト", "comparison_mode": "lowest"},
        "safety": {"request_delay_seconds": 2.0},
        "notifications": {"enabled": True, "discord_webhook_url": "https://discord.com/api/webhooks/123/abc"},
        "sources": [{"id": "a", "label": "A", "type": "json_ld", "url": "https://shop.example/a"}],
    }
    p = tmp_path / "config.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ConfigError, match="GitHub Secrets"):
        load_config(p)


def test_notifier_sends_to_discord_slack_and_ntfy_on_target_hit() -> None:
    cfg = load_config(TEMPLATE_ROOT / "config.json")
    fake_http = MagicMock()
    ok_resp = MagicMock()
    ok_resp.raise_for_status = MagicMock()
    fake_http.post.return_value = ok_resp

    alert = AlertRow(
        item_name="Sony WH-1000XM5",
        condition="新品",
        target_price_yen=42000,
        current_best_yen=41200,
        best_source_label="サンプル店Beta",
        diff_yen=-800,
        achieved=True,
        status_label="🎯 目標達成",
        url="https://shop-beta.example/p/101",
    )
    summary = {"fetched_at": "2026-11-26T17:17:00+09:00", "record_count": 10, "comparison_count": 4, "errors": {}}
    env = {
        "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/000/dummy",
        "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/T00/B00/dummy",
        "NTFY_TOPIC_URL": "https://ntfy.sh/demo-private-topic-xyz",
    }

    result = send_notifications(
        config=cfg,
        compared_rows=[],
        alert_rows=[alert],
        summary=summary,
        sheet_url="https://docs.google.com/spreadsheets/d/dummy/edit",
        env=env,
        session=fake_http,
    )
    assert result.sent_channels == ["discord", "slack", "ntfy"]
    assert result.errors is None
    assert fake_http.post.call_count == 3


def test_notifier_skips_when_no_target_hit_and_no_error() -> None:
    cfg = load_config(TEMPLATE_ROOT / "config.json")
    fake_http = MagicMock()

    alert = AlertRow(
        item_name="RICOH GR III",
        condition="中古",
        target_price_yen=135000,
        current_best_yen=139500,
        best_source_label="サンプル店Beta",
        diff_yen=4500,
        achieved=False,
        status_label="監視中",
    )
    result = send_notifications(
        config=cfg,
        compared_rows=[],
        alert_rows=[alert],
        summary={"fetched_at": "2026-11-26T17:17:00+09:00", "errors": {}},
        env={"NTFY_TOPIC_URL": "https://ntfy.sh/demo-topic"},
        session=fake_http,
    )
    assert result.sent_channels == []
    assert "スキップ" in result.skipped_reason
    fake_http.post.assert_not_called()


def test_cli_writes_markdown_step_summary_for_mobile_github_app(tmp_path: Path) -> None:
    md_file = tmp_path / "step_summary.md"
    exit_code = main(
        [
            "--config",
            str(TEMPLATE_ROOT / "config.json"),
            "--output-dir",
            str(tmp_path / "data"),
            "--markdown-summary",
            str(md_file),
            "--strict",
        ]
    )
    assert exit_code == 0
    md_text = md_file.read_text(encoding="utf-8")
    assert "## マイ価格比較ダッシュボード（デモ）" in md_text
    assert "🎯 目標価格に到達した商品" in md_text
    assert "Sony WH-1000XM5 ワイヤレスヘッドホン" in md_text
