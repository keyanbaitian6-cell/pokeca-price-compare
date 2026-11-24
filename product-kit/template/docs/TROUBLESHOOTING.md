# よくあるエラー解決集（トラブルシューティング）

エラーが出ても焦る必要はありません！まずは下の「症状別クイック早見表」から該当する項目を探してください。

---

## 症状別クイック早見表

| 起きている症状 | 該当セクション |
| --- | --- |
| `python` や `pip` が認識されない / ライブラリが入らない | [1. Python・環境構築系](#1-python環境構築系) |
| 取得件数が 0 件になる / 欲しい商品が取れない / robots.txt エラー | [2. データ取得・HTML構造系](#2-データ取得html構造系) |
| Google シートに書き込めない（403 / 404 / JSON エラー） | [3. Googleスプレッドシート連携系](#3-googleスプレッドシート連携系) |
| GitHub Actions が失敗する / 時間通りに動かない / 60日で止まった | [4. GitHub Actions 自動実行系](#4-github-actions-自動実行系) |
| スマホ手動更新ページで 401 / 403 / 429 / 502 が出る | [5. Vercel スマホ手動更新系](#5-vercel-スマホ手動更新系) |
| Excel で CSV が文字化けする / 同じ商品が別行に分かれる | [6. CSV・名寄せ・表示系](#6-csv名寄せ表示系) |

---

## 1. Python・環境構築系

### Q1-1：`python は内部コマンドまたは外部コマンドとして認識されていません`（Windows）
- **原因**: Python インストール時に「Add python.exe to PATH」のチェックが外れています。
- **解決策**:
  1. 代わりに `py -m venv .venv` を試してください（Windows 標準の Python ランチャー `py` なら動くことが多いです）。
  2. それでも動かない場合は Python インストーラーを再実行し、「Modify」から **Add Python to environment variables** にチェックを入れて再起動してください。

### Q1-2：Windows PowerShell で `.venv\Scripts\Activate.ps1` が実行ポリシーエラーになる
- **原因**: Windows の初期セキュリティ設定でスクリプト実行が制限されています。
- **解決策**: 仮想環境をアクティベートする必要はありません！マニュアル通り **`.\.venv\Scripts\python.exe`** を直接指定して実行すれば、セキュリティ設定を変更せずに安全に動きます。

### Q1-3：`config.json のJSON書式に誤りがあります`
- **原因**: `config.json` を手編集した際に、行末の余分なカンマ（最後の要素の後ろの `,`）や、ダブルクォート `"` の閉じ忘れが起きています。
- **解決策**: エラーメッセージに表示された行番号の前後を確認するか、[`AI_CUSTOMIZE_PROMPTS.md`](AI_CUSTOMIZE_PROMPTS.md) の「プロンプト 5」に `config.json`（秘密情報は除く）とエラー文を貼って修正してもらってください。

---

## 2. データ取得・HTML構造系

### Q2-1：`取得件数が0件でした` とエラーになる
考えられる原因は大きく 3 つです。

1. **CSS セレクタが実際の HTML と合っていない（またはサイトがリニューアルした）**
   - 解決策：ブラウザで右クリック →「検証」→「Copy outerHTML」で最新 HTML をコピーし、[`AI_CUSTOMIZE_PROMPTS.md`](AI_CUSTOMIZE_PROMPTS.md) の **プロンプト 1（またはプロンプト 8）** に貼ってセレクタを作り直してください。
2. **価格が JavaScript で後から読み込まれるサイト（SPA / 動的描画）である**
   - 確認方法：ブラウザで「右クリック → **ページのソースを表示**」を開き、画面に見えている「商品名」や「価格の数字」を検索（`Ctrl + F`）して **1件もヒットしない場合** は JavaScript 動的描画ページです。
   - 解決策：
     - まず同じページ内に `<script type="application/ld+json">`（`json_ld`）がないか確認します。
     - もし別ページに公開 CSV や HTML 版の価格表があればそちらを優先してください。
     - どうしてもブラウザ描画が必要な公開ページは、利用規約を再確認したうえで無料 AI に Playwright 併用への拡張を相談してください（ただし GitHub Actions の実行時間が増えます）。
3. **アクセスブロック（HTTP 403 / 429）が出ている**
   - 解決策：そのサイトが自動取得を制限しています。無理に回避せず、**対象から外して別の公開サイトを使ってください**（[`SAFE_USAGE_GUIDELINES.md`](SAFE_USAGE_GUIDELINES.md) 参照）。

### Q2-2：`対象サイトの robots.txt により取得が禁止されています`
- **原因**: 対象サイトの `https://ドメイン/robots.txt` が、その URL パスへの自動アクセスを禁止（`Disallow`）しています。
- **解決策**: サイト運営者の意思を尊重し、**その URL は監視対象から外してください**。同じサイト内の許可された公開ページや公式フィードがあるか確認しましょう。

### Q2-3：`安全運用ガード: safety.request_delay_seconds は 1.5 秒以上にしてください`
- **原因**: `config.json` の `request_delay_seconds` が `1.5` 未満になっています。
- **解決策**: 相手サーバーへの負荷防止のため、`2.0` 以上に設定してください。

---

## 3. Googleスプレッドシート連携系

### Q3-1：`APIError: [403]: The caller does not have permission` / `SpreadsheetNotFound`
- **原因**: 出力先スプレッドシートに、サービスアカウントのメールアドレスを「編集者」として共有し忘れています（または `OUTPUT_SPREADSHEET_ID` のコピペ間違い）。
- **解決策**:
  1. スプレッドシート右上の **「共有」** を開く。
  2. サービスアカウントのメール（`...@...iam.gserviceaccount.com`）が **「編集者」** で入っているか確認する。
  3. スプレッドシートIDに前後のスラッシュ `/` や `/edit` が混入していないか確認する。

### Q3-2：`Google Sheets API has not been used in project ... or it is disabled`
- **原因**: Google Cloud コンソールで `Google Sheets API` または `Google Drive API` の有効化が漏れています。
- **解決策**: エラーメッセージ内の URL を開くか、Google Cloud の「APIとサービス → ライブラリ」から **`Google Sheets API`** と **`Google Drive API`** の両方を有効にし、2〜3分待ってから再実行してください。

### Q3-3：`Could not deserialize key data` / `Invalid JSON`（GitHub Actions 実行時）
- **原因**: GitHub Secrets の `GOOGLE_CREDENTIALS_JSON` に貼り付けた JSON の一部が欠けているか、先頭/末尾に余計な文字が入っています。
- **解決策**: 元の `.json` ファイルをテキストエディタ（メモ帳や VS Code）で開き、**`{` から最後の `}` まで**を1文字も欠かさずコピーし直して Secret を更新してください。

---

## 4. GitHub Actions 自動実行系

### Q4-1：設定した時間ちょうどに自動更新されない
- **原因**: GitHub Actions 無料枠の仕様上、`schedule (cron)` は混雑時間帯（特に毎時 00 分ちょうど）に **5〜45 分ほど遅延** することがあります。不具合ではありません。
- **解決策**: もし少しでも遅延を減らしたい場合は、`cron: "0 8 * * *"` ではなく `"17 8 * * *"` のように **半端な分** にずらすと混雑を避けやすくなります。

### Q4-2：2ヶ月（60日）経ったら自動更新が急に止まった
- **原因**: GitHub の仕様により、**60日間コミットがないリポジトリは定期実行（cron）が自動停止**します。
- **解決策**: GitHub リポジトリの **`Actions` タブ** を開き、黄色いバナーの **`Enable workflow`** ボタンを1回クリックするだけで再開します。

### Q4-3：`エラー: GitHub Secrets に GOOGLE_CREDENTIALS_JSON と OUTPUT_SPREADSHEET_ID を登録してください`
- **原因**: リポジトリの `Settings > Secrets and variables > Actions` に Secret が未登録、または名前（大文字・アンダースコア）に 1 文字違いがあります。
- **解決策**: `Environment secrets` ではなく **`Repository secrets`** に正確なスペルで登録されているか確認してください。

---

## 5. Vercel スマホ手動更新系

### Q5-1：`401 合言葉が違います`
- **原因**: 入力した合言葉と、Vercel 環境変数 `UPDATE_PASSWORD_HASH` のハッシュが一致していません。
- **解決策**: `python3 scripts/make_passphrase_hash.py` でハッシュを作り直し、Vercel の環境変数を更新したあと、**Vercel で「Redeploy（再デプロイ）」**を実行してください（※Vercelは環境変数を変えただけでは反映されず、再デプロイが必要です）。

### Q5-2：`429 更新中または連続実行防止中です。約○分後にお試しください`
- **原因**: 正常な安全動作です！実行中または直近 5 分以内の連続起動を防止しています。
- **解決策**: 表示された分数だけ待ってから再度お試しください。

### Q5-3：`502 更新を開始できませんでした。GitHubトークンの有効期限や権限を確認してください`
- **原因**: 以下のいずれかです。
  1. Fine-grained トークンの **有効期限切れ**
  2. トークンの権限に **`Actions: Read and write`** が付いていない
  3. Vercel 環境変数の `GITHUB_OWNER` / `GITHUB_REPO` / `WORKFLOW_FILE` のスペル間違い
- **解決策**: GitHub で新しいトークンを再発行し、Vercel の `GITHUB_TOKEN` を更新して **Redeploy** してください。

### Q5-4：`403 このページから操作してください`
- **原因**: ブラウザのシークレット拡張機能や外部ツールから直接 `/api/update` を叩いたため、同一オリジン保護が働きました。
- **解決策**: 発行された Vercel の正規 URL（`https://...vercel.app`）をスマホ標準ブラウザ（Safari / Chrome）で開いて操作してください。

---

## 6. CSV・名寄せ・表示系

### Q6-1：同じ商品なのに店舗Aと店舗Bが「単独掲載」に分かれてしまった
- **原因**: 店舗ごとに商品名や「状態（新品 vs 標準 など）」の表記が異なっています。
- **解決策**:
  1. `全取得` タブ（または `data/raw_prices.csv`）で両店舗の「商品名（名寄せ後）」と「状態」を見比べます。
  2. 商品名がズレている場合は、[`AI_CUSTOMIZE_PROMPTS.md`](AI_CUSTOMIZE_PROMPTS.md) の **プロンプト 3** で `normalization` ルールを作って `config.json` に貼ります。
  3. 「状態」が片方だけ `標準` になっている場合は、`config.json` の `default_condition` を揃えます。

### Q6-2：価格推移の「30日推移（ミニグラフ）」が空欄のまま
- **原因**: `SPARKLINE` ミニグラフは **2日分以上の履歴** が溜まった時点で描画されます。初回実行日（1日分のみ）は空欄になるのが正常です。
- **解決策**: 翌日の自動更新が終わると自動でグラフが現れます！

---

## それでも解決しないとき（無料AIへ 10 秒で相談）

エラー画面のテキストをコピーして、[`AI_CUSTOMIZE_PROMPTS.md`](AI_CUSTOMIZE_PROMPTS.md) の **「プロンプト 5：エラーメッセージ丸投げ一発デバッグ」** を使って手元の無料 ChatGPT / Gemini / Claude に貼り付けてください。  
※ 認証JSON・トークン・合言葉だけは絶対に貼らないようご注意ください。
