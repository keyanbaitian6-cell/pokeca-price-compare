# ポケカ未開封BOX 買取価格比較

買取ソムリエ、コレクトの公開Google価格表、runtoから価格を取得し、未開封ポケモンカードBOXの比較CSVを作成します。元サイトへの購入・買取申込やログインは行いません。

対象サイト、名寄せ、手動更新、運用上のセキュリティ判断は
[判断記録](docs/DECISIONS.md)にまとめています。

## 取得元

- 買取ソムリエ（ポケモンカード）: <https://somurie-kaitori.com/products?category=2&subcategory=7>
- 買取ソムリエ（ポケモンカード・その他、現在0件）: <https://somurie-kaitori.com/products?category=2&subcategory=13>
- コレクト: <https://docs.google.com/spreadsheets/d/1uNtzhQBeiPmGR8rjqgwNdesCHbD4Nr6Y4ecZAjBE15g/htmlview>
- runto: <https://runto666.com/product-category/card/>

コレクトのシートは参照専用です。スクリプトはこのIDをGoogle出力先として拒否します。

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
- `data/run_summary.json`: 取得件数、状態推定件数、価格差20%超の検査結果、サイト別エラー

異なる実状態は別商品として扱います。片方のサイトだけ状態が `unspecified` の場合は同名商品の実状態行へ価格を補完し、内部データでは `condition_inferred` フラグ、閲覧用シートでは「一部店舗で状態不明」の注意を表示します。`shrink_wrapped` と `no_shrink` は統合しません。runtoの価格幅は商品詳細のバリエーションJSONを取得して、シュリンク有・無などを個別価格に展開します。

CSVと照合キーでは互換性のため英語の状態コードを維持します。閲覧用のGoogleスプレッドシートとExcelブックでは、`shrink_wrapped` を「シュリンク有」、`no_shrink` を「シュリンク無」、`no_perforation` を「ぺりぺり無」、`unspecified` を「状態不明」と表示します。

名寄せではUnicodeをNFKC正規化してからシリーズ名、状態語、BOX表記、M3/M5/M1Lなどの品番を除去します。買取ソムリエのカードに個別ページのリンクがない場合は一覧URLを保存し、将来リンクが追加された場合は個別URLを優先します。

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

出力先の「比較」「全取得」タブを毎回更新します。認証JSONはリポジトリへ保存しないでください。

## 定期更新

スマホから必要な時だけ更新する場合は [MANUAL_UPDATE_SETUP.md](MANUAL_UPDATE_SETUP.md) を参照してください。Vercelのスマホ用Webページ、合言葉、GitHub Actionsを使用し、自動スケジュールは設定しません。

常駐ループではなくOSのスケジューラーを推奨します。失敗ログやPC再起動後の再実行を管理しやすいためです。

### Windows タスク スケジューラ

操作には次を指定します。

- プログラム: `powershell.exe`
- 引数: `-NoProfile -ExecutionPolicy Bypass -File "C:\path\to\kakaku\scripts\run_compare.ps1"`
- 開始: `C:\path\to\kakaku`

Google出力も行う場合は、実行ユーザーの環境変数に以下を設定します。

```text
CARD_PRICE_OUTPUT_SHEET_ID=出力先ID
GOOGLE_APPLICATION_CREDENTIALS=C:\secure\service-account.json
```

### macOS cron例（1時間ごと）

```cron
0 * * * * cd /path/to/kakaku && .venv/bin/python -m card_price_compare >> data/scheduler.log 2>&1
```

更新間隔はサイト負荷を考慮し、まず1時間以上を推奨します。利用規約と公開範囲に変更がないか定期的に確認してください。

## 保守ポイント

- コレクト: `collectors/collect_sheet.py` の表列対応
- runto: `li.product`、`.price`、`form.variations_form`
- 買取ソムリエ: `.ant-card`
- 名寄せ: `normalize.py`

HTML構造変更で0件になった場合は正常終了させず、`run_summary.json`へエラーを記録します。アクセス間隔は既定1秒で、429/5xxには指数バックオフ付きで再試行します。
