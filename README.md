# ポケカ未開封BOX 買取価格比較

買取ソムリエ、コレクトの公開Google価格表、runtoから価格を取得し、未開封ポケモンカードBOXの比較CSVを作成します。元サイトへの購入・買取申込やログインは行いません。

対象サイト、名寄せ、手動更新、運用上のセキュリティ判断は
[判断記録](docs/DECISIONS.md)にまとめています。

## 取得元

- 買取ソムリエ（ポケモンカード）: <https://somurie-kaitori.com/products?category=2&subcategory=7>
- 買取ソムリエ（ポケモンカード・その他、現在0件）: <https://somurie-kaitori.com/products?category=2&subcategory=13>
- runto: <https://runto666.com/product-category/card/>
- コレクト（一時中断・既定の取得対象外）: <https://docs.google.com/spreadsheets/d/1uNtzhQBeiPmGR8rjqgwNdesCHbD4Nr6Y4ecZAjBE15g/htmlview>

コレクトのシートは参照専用です。スクリプトはこのIDをGoogle出力先として拒否します（現在、既定の取得対象からは一時中断しており、再開時は `--sources collect,runto,somurie` または既定値の変更で有効化できます）。

## セットアップ

Python 3.10以上を使用します。

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m playwright install chromium
```

### macOS / Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -e .
.venv/bin/python -m playwright install chromium
```

## 実行

```powershell
.\.venv\Scripts\python.exe -m card_price_compare
```

まずコレクトだけで疎通確認する場合:

```powershell
.\.venv\Scripts\python.exe -m card_price_compare --sources collect
```

出力:

- `data/raw_prices.csv`: 取得した全レコード
- `data/box_comparison.csv`: 同一商品・同一シュリンク状態で比較したBOX価格
- `data/shrink_trend_history.csv`: ローカル実行時に蓄積するシュリンク有BOXの日次推移履歴
- `data/market_insights.json`: 店舗名を匿名化した市況分析結果（前回比・7日前比ランキング、価格差注目BOX、地合いサマリー）
- `data/ai_prompts.md` / `data/ai_prompts.json`: 無料/Web版のChatGPT・Gemini・Claudeへそのまま貼れるX投稿用（3パターン）・週次note用プロンプト＆下書き素材（APIキー不要）
- `data/run_summary.json`: 取得件数、状態推定件数、価格差20%超の検査結果、地合い概要、サイト別エラー

外部サイトへアクセスせずに保存済みCSVからプロンプトだけ再生成する場合:

```bash
python -m card_price_compare --from-local-data --output-dir data
```

異なる実状態は別商品として扱います。片方のサイトだけ状態が `unspecified` の場合は同名商品の実状態行へ価格を補完し、内部データでは `condition_inferred` フラグ、閲覧用シートでは「注意」列に「状態推定」と表示します。`shrink_wrapped` と `no_shrink` は統合しません。runtoの価格幅は商品詳細のバリエーションJSONを取得して、シュリンク有・無などを個別価格に展開します。

CSVと照合キーでは互換性のため英語の状態コードを維持します。閲覧用のGoogleスプレッドシートとExcelブックでは、`shrink_wrapped` を「シュリンク有」、`no_shrink` を「シュリンク無」、`no_perforation` を「ぺりぺり無」、`unspecified` を「状態不明」と表示します。

名寄せではUnicodeをNFKC正規化してからシリーズ名、状態語、BOX表記、`SV8a`・`S12a`・`SM12a`・`M3`・`M5`・`M1L`などの品番を除去し、店舗間の別名（スペシャルBOX、デラックスBOX、`ポケモン GO`など）を統一します。買取ソムリエのカードに個別ページのリンクがない場合は一覧URLを保存し、将来リンクが追加された場合は個別URLを優先します。

## Googleスプレッドシート出力

1. Google CloudでSheets APIとDrive APIを有効化します。
2. サービスアカウントを作成し、JSON鍵をローカルに保存します。
3. **新しい出力用スプレッドシート**をサービスアカウントのメールアドレスと共有します。
4. 次を実行します。

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-google.txt
.\.venv\Scripts\python.exe -m card_price_compare `
  --google-spreadsheet-id "出力先ID" `
  --google-credentials "C:\secure\service-account.json"
```

出力先の各タブを毎回整形・更新します（認証JSONはリポジトリへ保存しないでください）。

- **サマリー**: 最新集計カウンター、手動更新ページへのリンク、取得元一覧
- **比較**: 2サイト以上が掲載しているシュリンク有BOXを差率（価格差÷最高買取価格）の降順で表示。前日以前の直近記録との「前回比」も併記
- **価格推移（シュリンク有）**: 1商品1行の横型マトリクスで「最新最高値・最高値の店・前回比・7日前比・30日推移（`SPARKLINE`ミニグラフ）・直近最大30回分の日付別価格（新しい順）」を表示。全期間の日次生データは非表示の「推移データ（保管用）」シートへ自動蓄積
- **単独掲載**: 1サイトのみ掲載の商品を、買取価格の降順で分離表示
- **更新履歴**: 実行履歴を新しい順（最新が2行目）で表示
- **全取得**: 取得した全レコード（元の商品名・URLの確認用）
- **発信プロンプト**: 特定店舗名を匿名化した市況ダイジェスト、毎日のX投稿用プロンプト3パターン（速報系／気づき系／ツール誘導系）、週次note記事作成用プロンプト、クイック下書きベース、無料計算ツール「トレカ損益ラボ」誘導テンプレートを1セルずつ配置（D列をコピーしてWeb版生成AIへそのまま貼付可能）

## 生成AI連携・X/note収益化＆無料ツール連携

- X/note発信＆収益化ロードマップ・投稿ルーティン: [docs/X_NOTE_MONETIZATION_PLAYBOOK.md](docs/X_NOTE_MONETIZATION_PLAYBOOK.md)
- 無料計算ツール集「トレカ損益ラボ」（`site/`）収益化ガイド: [MONETIZATION_GUIDE.md](MONETIZATION_GUIDE.md)

## 自動更新・手動更新

GitHub Actionsのスケジュールにより、毎日13:42（日本時間）ごろに自動で価格表を更新します。
スマホから任意のタイミングで手動更新する場合は [MANUAL_UPDATE_SETUP.md](MANUAL_UPDATE_SETUP.md) を参照してください。Vercelのスマホ用Webページ、合言葉、GitHub Actionsを使用します。

## 保守ポイント

- コレクト: `collectors/collect_sheet.py` の表列対応
- runto: `li.product`、`.price`、`form.variations_form`
- 買取ソムリエ: `.ant-card`
- 名寄せ: `normalize.py`

HTML構造変更で0件になった場合は正常終了させず、`run_summary.json`へエラーを記録します。アクセス間隔は既定1秒で、429/5xxには指数バックオフ付きで再試行します。
