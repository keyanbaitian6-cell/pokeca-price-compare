# 月額サーバー代0円で動く「自分専用・価格監視＆比較スプレッドシート自動構築キット」

ご購入ありがとうございます！  
このキットは、**有料サーバー・有料AI API・複雑なプログラミングを一切使わず**に、あなたがチェックしたい複数サイトの価格を自動で収集・比較し、見やすい Google スプレッドシートへ毎日自動更新できる個人用テンプレートパッケージです。

---

## このキットでできること

- **月額サーバー代 0 円・AI API 課金 0 円**
  - 自動実行は GitHub Actions（無料枠）、閲覧＆履歴管理は Google スプレッドシート（無料）、スマホからの即時手動更新は Vercel（無料枠）で構成されています。
- **「安く買う」「高く売る」どちらにも対応**
  - 家電・スニーカー・中古カメラ・推し活グッズなどの **最安値比較（`lowest` モード）**
  - トレカ・レトロゲーム・中古カメラなどの **買取最高値比較（`highest` モード）**
- **設定は `config.json` 1 ファイルで完結**
  - HTML 一覧ページ・個別商品ページ・JSON-LD（構造化データ）・公開 CSV の 4 方式に標準対応。さらに複雑なサイトも、付属の **「無料生成 AI カスタマイズプロンプト集」** で無料版 ChatGPT / Gemini / Claude にコードを書かせて追加できます。
- **7 タブ自動整形の Google スプレッドシート**
  - `サマリー` / `比較`（ベスト価格の緑ハイライト・差額/差率強調・前回比色分け）/ `価格推移`（30日ミニグラフ `SPARKLINE` 付き）/ `目標アラート`（買い時・売り時自動判定）/ `単独掲載` / `更新履歴` / `全取得` を毎回自動生成します。
- **安全運用ガード標準搭載**
  - 取得間隔の下限強制（1.5秒以上・既定2.0秒）、ページ巡回上限、`robots.txt` 自動確認、手動更新の5分クールダウンを組み込んでいます。

---

## 最短スタートマップ（まずは3分でデモを動かそう！）

```text
[Step 0] 安全運用ガイドラインを確認（2分）
    └─ docs/SAFE_USAGE_GUIDELINES.md を一読する
           │
           ▼
[Step 1] 付属サンプルでデモ実行（3分・外部通信ゼロ）
    └─ python3 scripts/run_demo.py を実行して CSV と比較結果を見る
           │
           ▼
[Step 2] config.json を自分の監視したいサイトへ書き換え（15分）
    └─ コード不要！ docs/AI_CUSTOMIZE_PROMPTS.md を無料AIにコピペするだけ
           │
           ▼
[Step 3] Google スプレッドシート連携（15分）
    └─ docs/SETUP_GUIDE.md の図解どおりにサービスアカウントを設定
           │
           ▼
[Step 4] GitHub Actions で毎日自動更新（10分）
    └─ 非公開リポジトリへアップロード＆Secrets登録で完全自動化
           │
           ▼
[Step 5] （任意）Vercel でスマホ手動更新ボタンを設置（10分）
    └─ 合言葉を入れるだけで、外出先からもスマホ1タップで即時更新
```

---

## まずは 3 分お試し（外部アクセスなしのローカルデモ）

パソコンに Python 3.10 以上が入っていれば、以下の 3 行で付属サンプルページ（`sample_pages/`）を使った価格比較を今すぐ体験できます。

### Windows（PowerShell）

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\run_demo.py
```

### macOS / Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/run_demo.py
```

実行が終わると `data/` フォルダに以下のファイルが作成されます（Excel で文字化けせずそのまま開けます）。

- `data/comparison.csv`：2 サイト以上で見つかった商品の比較表（差率・差額・目標判定付き）
- `data/alerts.csv`：設定した目標価格に到達した商品の一覧
- `data/single_listings.csv`：1 サイトのみ掲載の商品一覧
- `data/raw_prices.csv`：取得した全生データ（在庫切れ・商品 URL 含む）
- `data/run_summary.json`：取得件数とエラー状況のレポート

---

## 同梱ファイル一覧

| パス | 内容 |
| --- | --- |
| `config.json` | **メイン設定ファイル**（ここを編集するだけでOK。初期状態はオフラインデモ設定） |
| `config.examples/` | ジャンル別ひな形（家電最安・レトロゲーム/カメラ買取・スニーカー/推し活・トレカ汎用） |
| `docs/SETUP_GUIDE.md` | **図解付き完全導入マニュアル**（Googleシート連携・GitHub Actions・スマホ手動更新まで） |
| `docs/AI_CUSTOMIZE_PROMPTS.md` | **【目玉特典】購入者向け・無料生成AIカスタマイズプロンプト集**（ChatGPT/Gemini/Claude無料版対応） |
| `docs/TROUBLESHOOTING.md` | **よくあるエラー解決集**（症状別逆引き＋AI丸投げテンプレート） |
| `docs/SAFE_USAGE_GUIDELINES.md` | **安全な運用ガイドライン**（必ず最初に確認してください） |
| `src/price_monitor/` | 汎用価格監視・名寄せ・比較・スプレッドシート出力エンジン本体 |
| `custom_collectors/` | 無料AIで作った独自サイト用スクリプトを置くプラグインフォルダ |
| `mobile_updater/` | スマホから合言葉で手動更新できる Vercel 用 Web ページ一式 |
| `.github/workflows/update-prices.yml` | 毎日自動更新する GitHub Actions ワークフロー |
| `scripts/run_demo.py` | 1 コマンドでデモ動作確認するスクリプト |
| `scripts/make_passphrase_hash.py` | スマホ手動更新の合言葉ハッシュを安全に生成するツール |
| `sample_pages/` | デモ＆テスト用のサンプル公開 HTML / CSV 群 |
| `tests/` | 動作確認用自動テスト一式（`pytest` で実行可能） |

---

## 次に読むべきドキュメント

1. まず必読：[`docs/SAFE_USAGE_GUIDELINES.md`](docs/SAFE_USAGE_GUIDELINES.md)
2. 導入手順：[`docs/SETUP_GUIDE.md`](docs/SETUP_GUIDE.md)
3. 自分のサイトに対応させる：[`docs/AI_CUSTOMIZE_PROMPTS.md`](docs/AI_CUSTOMIZE_PROMPTS.md)
4. 困ったとき：[`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md)
