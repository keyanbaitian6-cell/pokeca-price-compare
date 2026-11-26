# 月額サーバー代0円で動く「自分専用・価格監視＆比較スプレッドシート自動構築キット」v2.0

ご購入ありがとうございます！  
このキットは、**有料サーバー・有料AI API・複雑なプログラミングを一切使わず**に、あなたがチェックしたい複数サイトの価格を自動で収集・比較し、見やすい Google スプレッドシート更新＆スマホプッシュ通知まで毎日自動化する個人用テンプレートパッケージです。

---

## v2.0 の 5 大特徴（月額 0 円・API 課金ゼロ）

1. **Python インストール不要！ブラウザ＆スマホだけでも導入可能**
   - 同梱の **`tools/config_builder.html`** をブラウザで開けば、フォーム入力だけでカンマミスゼロの `config.json`・合言葉ハッシュ・cron・AIプロンプトを作成できます。
   - GitHub Actions の **`run_mode=demo`** を使えば、PC に Python を入れずにクラウド上だけで即お試し実行できます。
2. **「安く買う」「高く売る」どちらにも対応**
   - 家電・スニーカー・中古カメラ・推し活グッズなどの **最安値比較（`lowest` モード）**
   - トレカ・レトロゲーム・中古カメラなどの **買取最高値比較（`highest` モード）**
3. **LINE Notify 終了後の「無料スマホプッシュ通知」を標準内蔵**
   - 目標価格に到達した日（またはエラー発生時）だけ、**ntfy.sh（アカウント登録すら不要！）／Discord／Slack** へ自動通知します。
4. **7 タブ自動整形 Google スプレッドシート ＋ GitHub スマホアプリ用サマリー表**
   - `サマリー` / `比較`（緑ハイライト・差額/差率強調・前回比）/ `価格推移`（30日 `SPARKLINE` ミニグラフ）/ `目標アラート` / `単独掲載` / `更新履歴` / `全取得` を毎回自動生成。
   - さらに GitHub Actions のジョブサマリーにも Markdown 比較表が出るので、GitHub 公式スマホアプリからも即確認できます。
5. **商用/副業利用も安心な 3 方式のスマホ手動更新＆安全運用ガード標準搭載**
   - ① **GitHub 公式スマホアプリ直起動（推奨・0分設定・商用OK）** ② **Cloudflare Workers 無料枠（1日10万req・商用OK）** ③ **Vercel Hobby（個人の趣味・非商用限定）** の 3 方式に対応。
   - 取得間隔の最小 1.5 秒ガード（既定 2.0 秒）・巡回上限 20 ページ・`robots.txt` 自動確認・5 分クールダウンをプログラム側で強制します。

---

## あなたに合う導入ルートを選ぼう

| ルート | おすすめの人 | 必要なもの |
| --- | --- | --- |
| **ルート A：ブラウザ完結ルート（推奨）** | PC に Python を入れたくない／非エンジニア／スマホ中心 | ブラウザ＋無料 GitHub・Google アカウントのみ |
| **ルート B：ローカル PC お試しルート** | 自分の PC でまず 3 分でオフラインデモを動かしたい | Python 3.10 以上＋PC |

詳しい手順はすべて **[`docs/SETUP_GUIDE.md`](docs/SETUP_GUIDE.md)** に図解入りでまとめています。

---

## PC で今すぐ 3 分お試し（ルート B・外部通信ゼロ）

```bash
# macOS / Linux（Windows PowerShell は .venv\Scripts\python.exe に読み替え）
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/run_demo.py
```

`data/` フォルダに Excel で文字化けしない UTF-8 BOM 付き CSV（`comparison.csv` / `alerts.csv` / `single_listings.csv` / `raw_prices.csv`）が出力されます。

---

## 同梱ファイル一覧（v2.0.0）

| パス | 内容 |
| --- | --- |
| `tools/config_builder.html` | **【目玉同梱ツール】** オフライン動作のビジュアル設定ビルダー（`config.json`作成・SHA-256ハッシュ生成・JST→UTC cron計算・無料AIプロンプト組立） |
| `config.json` | メイン設定ファイル（初期状態はすぐ動くオフラインデモ設定） |
| `config.examples/` | ジャンル別ひな形 4 種（家電最安・レトロゲーム/カメラ買取・スニーカー/推し活・トレカ汎用） |
| `docs/SETUP_GUIDE.md` | **図解付き完全導入マニュアル**（Python不要ルートA・ローカルルートB・無料通知・スマホ手動更新3方式） |
| `docs/AI_CUSTOMIZE_PROMPTS.md` | **【差別化特典】** 購入者向け・無料生成AIカスタマイズプロンプト集（API課金ゼロ） |
| `docs/TROUBLESHOOTING.md` | 症状別・よくあるエラー解決集 |
| `docs/SAFE_USAGE_GUIDELINES.md` | 安全な運用ガイドライン＆日本の関連4法令ガイド（必読） |
| `src/price_monitor/` | 汎用取得・名寄せ・比較・無料プッシュ通知（`notifier.py`）・Googleシート7タブ自動整形エンジン |
| `custom_collectors/` | 無料AIで作った独自サイト用コレクター置き場（動作確認済みサンプル入り） |
| `.github/workflows/update-prices.yml` | 毎日自動実行＋スマホアプリから4モード選択できる GitHub Actions 設定 |
| `mobile_updater/` | スマホ1タップ手動更新ページ（**Cloudflare Workers 商用OK版** ＆ **Vercel 非商用版** の両対応） |
| `scripts/run_demo.py` | 1 コマンドオフラインデモ実行スクリプト |
| `scripts/make_passphrase_hash.py` | 合言葉 SHA-256 ハッシュ生成ツール（PC CLI版） |
| `sample_pages/` | デモ＆テスト用公開 HTML / CSV 群（5 ファイル） |
| `tests/` | 自動テスト一式（`pytest` で実行可能） |

---

## 最初に読む順番

1. 必読（2分）：[`docs/SAFE_USAGE_GUIDELINES.md`](docs/SAFE_USAGE_GUIDELINES.md)
2. ツールを開く（1分）：`tools/config_builder.html` をブラウザでダブルクリック
3. 導入手順：[`docs/SETUP_GUIDE.md`](docs/SETUP_GUIDE.md)
4. 自分のサイト対応：[`docs/AI_CUSTOMIZE_PROMPTS.md`](docs/AI_CUSTOMIZE_PROMPTS.md)
5. 困ったとき：[`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md)
