from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

TEMPLATE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TEMPLATE_ROOT / "src"))

from price_monitor.config import ConfigError, SafetyConfig, load_config  # noqa: E402
from price_monitor.http_client import PoliteHttpClient, RobotsDisallowedError  # noqa: E402


def test_default_config_and_all_examples_are_valid() -> None:
    cfg = load_config(TEMPLATE_ROOT / "config.json")
    assert cfg.project.comparison_mode == "lowest"
    assert len(cfg.enabled_sources) == 4
    assert cfg.safety.request_delay_seconds >= 1.5

    example_files = sorted((TEMPLATE_ROOT / "config.examples").glob("*.json"))
    assert len(example_files) >= 4
    for example in example_files:
        example_cfg = load_config(example)
        assert len(example_cfg.enabled_sources) >= 1
        assert example_cfg.safety.request_delay_seconds >= 1.5


def test_rejects_unsafe_short_delay(tmp_path: Path) -> None:
    bad = {
        "project": {"title": "テスト", "comparison_mode": "lowest"},
        "safety": {"request_delay_seconds": 0.5},
        "sources": [{"id": "a", "label": "A", "type": "json_ld", "url": "https://shop.example/a"}],
    }
    p = tmp_path / "config.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ConfigError, match="1.5 秒以上"):
        load_config(p)


def test_rejects_excessive_max_pages(tmp_path: Path) -> None:
    bad = {
        "project": {"title": "テスト", "comparison_mode": "lowest"},
        "safety": {"request_delay_seconds": 2.0, "max_pages_per_source": 50},
        "sources": [{"id": "a", "label": "A", "type": "json_ld", "url": "https://shop.example/a"}],
    }
    p = tmp_path / "config.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ConfigError, match="1〜20"):
        load_config(p)


def test_rejects_disallowed_url_scheme_and_path_traversal(tmp_path: Path) -> None:
    bad_scheme = {
        "project": {"title": "テスト", "comparison_mode": "lowest"},
        "safety": {"request_delay_seconds": 2.0},
        "sources": [{"id": "a", "label": "A", "type": "json_ld", "url": "file:///etc/passwd"}],
    }
    p = tmp_path / "bad_scheme.json"
    p.write_text(json.dumps(bad_scheme), encoding="utf-8")
    with pytest.raises(ConfigError, match="URLスキーム"):
        load_config(p)

    bad_traversal = {
        "project": {"title": "テスト", "comparison_mode": "lowest"},
        "safety": {"request_delay_seconds": 2.0},
        "sources": [{"id": "a", "label": "A", "type": "json_ld", "url": "../outside.html"}],
    }
    p2 = tmp_path / "bad_traversal.json"
    p2.write_text(json.dumps(bad_traversal), encoding="utf-8")
    with pytest.raises(ConfigError, match="プロジェクトフォルダ外"):
        load_config(p2)


def test_robots_txt_blocks_disallowed_url(tmp_path: Path) -> None:
    fake_session = MagicMock()
    robots_resp = MagicMock(status_code=200, text="User-agent: *\nDisallow: /private/\n")
    page_resp = MagicMock(status_code=200, text="<html>ok</html>", encoding="utf-8")
    page_resp.raise_for_status = MagicMock()

    def fake_get(url: str, timeout: float = 20.0) -> MagicMock:
        if url.endswith("/robots.txt"):
            return robots_resp
        return page_resp

    fake_session.get.side_effect = fake_get
    client = PoliteHttpClient(
        SafetyConfig(request_delay_seconds=1.5, respect_robots_txt=True),
        base_dir=tmp_path,
        session=fake_session,
    )
    client.delay_seconds = 0.0  # テスト高速化のためモック環境のみ待機ゼロ

    with pytest.raises(RobotsDisallowedError):
        client.fetch_text("https://shop.example/private/items")

    assert client.fetch_text("https://shop.example/public/items") == "<html>ok</html>"
