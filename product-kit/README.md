# デジタル商品キット管理ガイド（販売者向け・v2.0.0）

このディレクトリ（`product-kit/`）は、既存のポケカ運用コード（`src/card_price_compare/`, `vercel/`, `.github/workflows/manual-update.yml`）および無料Webツール集（`site/*.html`）から **完全に独立** した、販売用デジタル商品パッケージです。

- **商品名**: 月額サーバー代0円で動く『自分専用・価格監視＆比較スプレッドシート自動構築キット』v2.0
- **公開ライブ体験LP**: [`site/price-kit/`](../site/price-kit/index.html) → GitHub Pages 公開 URL: <https://keyanbaitian6-cell.github.io/pokeca-price-compare/price-kit/>
- **Deep Search 調査＆設計書**: [`docs/DEEP_RESEARCH_AND_STRATEGY.md`](./docs/DEEP_RESEARCH_AND_STRATEGY.md)
- **収益モデル**: デジタル商品本体販売（note / BOOTH / Brain / Tips：1,980〜4,980円）＋ 個別カスタマイズ導線
- **厳守設計**: 有料AI APIキー不使用 / 楽天ROOM不使用 / 安全運用ガード内蔵（取得間隔1.5秒下限・`robots.txt`自動確認・公開ページ限定・商用OKインフラ対応）

---

## v2.0.0 で強化された 5 つのポイント（Deep Search 反映）

1. **Python インストール不要！ブラウザ＆スマホ完結導入ルート**（GitHub Actions の `run_mode=demo` ＋ Job Summary Markdown 比較表）
2. **同梱オフラインツール `template/tools/config_builder.html`**（`config.json` ビジュアル作成・SHA-256 ハッシュ生成・JST→UTC cron 計算・無料 AI プロンプト組立）
3. **無料スマホプッシュ通知 `src/price_monitor/notifier.py` を標準内蔵**（LINE Notify 終了後の 3 大代替：ntfy.sh / Discord / Slack・API 課金 0 円）
4. **商用/副業利用も規約準拠のスマホ手動更新 3 方式**（GitHub Mobile 直起動〔推奨・0分〕／Cloudflare Workers `cloudflare_worker.js`〔商用 OK〕／Vercel Hobby〔個人非営利限定〕）
5. **購入前に触れる公開ライブデモ LP（`site/price-kit/`）** を GitHub Pages へ自動公開

---

## 出荷・テスト・ZIP生成コマンド（リポジトリルートから実行）

```bash
# 1. Pythonテスト環境（初回のみ）
python3 -m venv product-kit/.venv
product-kit/.venv/bin/python -m pip install -r product-kit/template/requirements-dev.txt

# 2. 全テスト実行（Python本体＋通知＋ZIP検証 ＋ Node Vercel/Cloudflare Workerテスト）
product-kit/.venv/bin/pytest -v product-kit/template/tests product-kit/tests
node --test product-kit/template/mobile_updater/test/*.test.js

# 3. 配布用ZIPを 1 コマンドで生成＆セキュリティ自動検査
python3 product-kit/scripts/build_release_zip.py --version 2.0.0
```

出力先：`product-kit/dist/price-monitor-kit-v2.0.0.zip`（`.gitignore` 対象）。

---

## 販売公開までの最短ステップ

1. 公開ライブデモ <https://keyanbaitian6-cell.github.io/pokeca-price-compare/price-kit/> をスマホ・PC で開いて動作を確認する。
2. 上記コマンドで `product-kit/dist/price-monitor-kit-v2.0.0.zip` を生成する。
3. （任意）実機 Google スプレッドシートのスクショを撮る場合は `publish_demo_sheet.py` で過去7日分＋当日のデモデータを一発出力する：
   ```powershell
   product-kit\.venv\Scripts\python.exe -m pip install -r product-kit\template\requirements-google.txt
   product-kit\.venv\Scripts\python.exe product-kit\scripts\publish_demo_sheet.py --spreadsheet-id "デモ用スプレッドシートID" --credentials "C:\secure\google-credentials.json"
   ```
4. `apply_sales_urls.py` で `sales/` 原稿と `site/price-kit/index.html` の URL プレースホルダーを一括差し替えし、note / BOOTH / Brain / Tips へ ZIP を添付して公開する：
   ```powershell
   product-kit\.venv\Scripts\python.exe product-kit\scripts\apply_sales_urls.py --sales-url "https://..." --form-url "https://..." --dry-run
   ```
5. `sales/X_LAUNCH_THREAD.md` を使って X でローンチ告知する（ライブデモ URL 付き）。
6. **収益防衛（本格販売時）**：[`docs/PRIVATE_REPO_MIGRATION.md`](./docs/PRIVATE_REPO_MIGRATION.md) と `scripts/prepare_private_repo.py` を使い、有料本体を別 Private リポジトリへ分離する。
