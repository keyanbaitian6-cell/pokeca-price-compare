from __future__ import annotations

import logging
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import MIN_SAFE_DELAY_SECONDS, SafetyConfig


LOGGER = logging.getLogger(__name__)


class RobotsDisallowedError(RuntimeError):
    """対象サイトの robots.txt により自動取得が許可されていない場合のエラー。"""


class PoliteHttpClient:
    """安全ガード（取得間隔強制・robots.txt確認・指数バックオフ）付きHTTPクライアント。

    ローカルのサンプルファイル（sample_pages/...）の場合は外部通信せず直接読み込みます。
    """

    def __init__(
        self,
        safety: SafetyConfig,
        *,
        base_dir: Path,
        session: requests.Session | None = None,
    ) -> None:
        self.delay_seconds = max(float(safety.request_delay_seconds), MIN_SAFE_DELAY_SECONDS)
        self.timeout_seconds = float(safety.timeout_seconds)
        self.respect_robots_txt = bool(safety.respect_robots_txt)
        self.user_agent = safety.user_agent
        self.base_dir = base_dir.resolve()
        self.session = session or self._build_session(self.user_agent)
        self._last_request_at = 0.0
        self._robots_cache: dict[str, RobotFileParser | None] = {}

    @staticmethod
    def _build_session(user_agent: str) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=1.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept-Language": "ja,en;q=0.8",
            }
        )
        return session

    def _sleep_if_needed(self) -> None:
        if self._last_request_at <= 0:
            return
        elapsed = time.monotonic() - self._last_request_at
        remaining = self.delay_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def _check_robots_txt(self, url: str) -> None:
        if not self.respect_robots_txt:
            return
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in self._robots_cache:
            robots_url = f"{origin}/robots.txt"
            parser = RobotFileParser()
            parser.set_url(robots_url)
            try:
                self._sleep_if_needed()
                response = self.session.get(robots_url, timeout=min(self.timeout_seconds, 10.0))
                self._last_request_at = time.monotonic()
                if response.status_code == 200:
                    parser.parse(response.text.splitlines())
                    self._robots_cache[origin] = parser
                elif response.status_code in {401, 403}:
                    # アクセス制限がある robots.txt は保守的に不許可として扱う
                    parser.parse(["User-agent: *", "Disallow: /"])
                    self._robots_cache[origin] = parser
                else:
                    # 404 等は明示的禁止なし
                    self._robots_cache[origin] = None
            except requests.RequestException as exc:
                LOGGER.warning("robots.txt の確認に失敗しました (%s): %s", robots_url, exc)
                self._robots_cache[origin] = None

        cached = self._robots_cache[origin]
        if cached is not None and not cached.can_fetch(self.user_agent, url):
            raise RobotsDisallowedError(
                f"対象サイトの robots.txt により取得が禁止されています: {url}\n"
                "利用規約と robots.txt を確認し、取得許可のある公開ページのみを対象にしてください。"
            )

    def fetch_text(self, target: str) -> str:
        """URLまたはプロジェクト内ローカルファイルのテキストを取得する。"""
        parsed = urlparse(target)
        if parsed.scheme in {"http", "https"}:
            self._check_robots_txt(target)
            self._sleep_if_needed()
            response = self.session.get(target, timeout=self.timeout_seconds)
            self._last_request_at = time.monotonic()
            response.raise_for_status()
            if not response.encoding or response.encoding.lower() == "iso-8859-1":
                response.encoding = response.apparent_encoding or "utf-8"
            return response.text

        # ローカルサンプルファイル（デモ・テスト用）
        local_path = (self.base_dir / target).resolve()
        try:
            local_path.relative_to(self.base_dir)
        except ValueError as exc:
            raise ValueError(f"許可されていないローカルパスです: {target}") from exc
        if not local_path.exists():
            raise FileNotFoundError(f"ローカルファイルが見つかりません: {local_path}")
        return local_path.read_text(encoding="utf-8-sig")
