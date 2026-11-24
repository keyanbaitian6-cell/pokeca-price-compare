# デジタル商品キット管理ガイド（販売者向け）

このディレクトリ（`product-kit/`）は、既存のポケカ運用コード（`src/card_price_compare/`, `vercel/`, `.github/workflows/manual-update.yml`）および無料Webツール集（`site/`, `.github/workflows/deploy-pages.yml`）から **完全に独立** した、販売用デジタル商品パッケージです。

**商品名**: 月額サーバー代0円で動く『自分専用・価格監視＆比較スプレッドシート自動構築キット』  
**収益モデル**: デジタル商品本体販売（note / BOOTH / Brain / Tips：1,980〜4,980円）＋ 個別カスタマイズ導線  
**厳守設計**: 有料AI APIキー不使用 / 楽天ROOM不使用 / 安全運用ガード内蔵（取得間隔1.5秒下限・`robots.txt`自動確認・公開ページ限定）

---

## ディレクトリ構成

```text
product-kit/
├── README.md                          # このファイル（販売者向け出荷＆検証手順）
├── .gitignore                         # dist/・.venv/・認証JSON等を除外
├── template/                          # ★購入者へ配布するZIPの中身そのもの
│   ├── README.md                      # 購入者向けスタートガイド
│   ├── config.json                    # 1ファイル完結設定（オフラインデモ設定済み）
│   ├── config.examples/               # ジャンル別設定ひな形4種
│   ├── src/price_monitor/             # 汎用取得・名寄せ・比較・CSV/Googleシート出力エンジン
│   ├── custom_collectors/             # 無料AI生成カスタムコレクター用プラグイン領域
│   ├── mobile_updater/                # スマホ手動更新（Vercel汎用版）＋Nodeテスト
│   ├── .github/workflows/             # 毎日自動更新 GitHub Actions ワークフロー
│   ├── sample_pages/                  # 外部アクセスゼロのデモ＆テスト用公開HTML/CSV
│   ├── scripts/                       # 1コマンドデモ(run_demo.py)＆合言葉ハッシュ生成ツール
│   ├── docs/
│   │   ├── SETUP_GUIDE.md             # 非エンジニア向け・図解付き導入マニュアル
│   │   ├── AI_CUSTOMIZE_PROMPTS.md    # 【目玉特典】無料生成AIカスタマイズプロンプト集
│   │   ├── TROUBLESHOOTING.md         # よくあるエラー解決集
│   │   └── SAFE_USAGE_GUIDELINES.md   # 安全な運用ガイドライン
│   └── tests/                         # テンプレート自動テスト一式
├── scripts/
│   └── build_release_zip.py           # ★1コマンドで配布ZIP生成＆秘密情報・不要ファイル自動検査
├── tests/
│   └── test_release_packaging.py      # ZIP生成・セキュリティ検査・解凍後デモ動作テスト
└── sales/                             # 販売用LP・集客・価格設計一式（そのままコピペ可能）
    ├── PRICING_AND_FUNNEL.md          # 価格設計（1,980〜4,980円）＆カスタマイズ導線設計
    ├── LP_NOTE.md                     # note販売用記事原稿
    ├── LP_BOOTH.md                    # BOOTH商品ページ原稿
    ├── LP_BRAIN_TIPS.md               # Brain / Tips販売用セールスレター
    └── X_LAUNCH_THREAD.md             # 告知用Xスレッド＆単発ポスト原稿
```

---

## 出荷・テスト・ZIP生成コマンド（リポジトリルートから実行）

### 1. テスト環境の準備（初回のみ）

```bash
python3 -m venv product-kit/.venv
product-kit/.venv/bin/python -m pip install -r product-kit/template/requirements-dev.txt
```

### 2. 全テストを実行する（テンプレート本体＋モバイル更新＋ZIPパッケージ検査）

```bash
product-kit/.venv/bin/pytest -v product-kit/template/tests product-kit/tests
node --test product-kit/template/mobile_updater/test/update.test.js
```

### 3. 配布用ZIPを 1 コマンドで生成＆自動検証する

```bash
python3 product-kit/scripts/build_release_zip.py --version 1.0.0
```

成功すると `product-kit/dist/price-monitor-kit-v1.0.0.zip` が生成され、同時に以下が自動検証されます：

- `.env` / `*credentials*.json` / `*service-account*.json` / `__pycache__` / `data/` 等の不要・機密ファイルが **0件** であること
- 秘密鍵・APIキー・GitHubトークン・既存ポケカ運用リポジトリ固有のユーザー名や本番スプレッドシートID・実店舗URLが **一切含まれていない** こと
- 必須ファイル（設定・コード・ワークフロー・マニュアル4種・プロンプト集・スマホ更新一式）がすべて揃っていること
- ZIPアーカイブのCRC整合性が正常であること

---

## 販売公開の最短 4 ステップ

1. 上記コマンドで `product-kit/dist/price-monitor-kit-v1.0.0.zip` を生成する。
2. 付属デモを自分用のデモ Google スプレッドシートへ 1 回出力し、「比較」「価格推移」「目標アラート」タブのスクリーンショットを 3 枚撮る（商品ページの訴求力が大きく上がります）。
3. `sales/LP_NOTE.md` / `sales/LP_BOOTH.md` / `sales/LP_BRAIN_TIPS.md` を各プラットフォームへ貼り付け、生成した ZIP とスクショを添付して公開する。
4. `sales/X_LAUNCH_THREAD.md` を使って X でローンチ告知する（価格改定計画は `sales/PRICING_AND_FUNNEL.md` を参照）。
