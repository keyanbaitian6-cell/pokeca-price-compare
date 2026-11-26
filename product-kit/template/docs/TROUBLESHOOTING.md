# よくあるエラー解決集（トラブルシューティング v2.0）

エラーが出ても焦る必要はありません！まずは下の「症状別クイック早見表」から該当項目を探してください。

---

## 症状別クイック早見表

| 起きている症状 | 該当セクション |
| --- | --- |
| `python` がない / JSON書式エラー / `config_builder.html` の使い方 | [1. 環境構築・config.json系](#1-環境構築configjson系) |
| 取得件数 0 件 / JavaScript 動的ページ / `robots.txt` エラー | [2. データ取得・HTML構造系](#2-データ取得html構造系) |
| Google シート 403 / API 無効 / JSON パースエラー | [3. Googleスプレッドシート連携系](#3-googleスプレッドシート連携系) |
| GitHub Actions 遅延 / 60 日停止 / Secrets 未設定 | [4. GitHub Actions 自動実行系](#4-github-actions-自動実行系) |
| 無料スマホ通知（ntfy.sh / Discord / Slack）が届かない | [5. 無料プッシュ通知系](#5-無料プッシュ通知系) |
| スマホ手動更新（Cloudflare Workers / Vercel）の 401 / 403 / 429 / 502 | [6. スマホ手動更新ページ系](#6-スマホ手動更新ページ系) |
| 同じ商品が別行に分かれる / 30日ミニグラフが空欄 | [7. 名寄せ・表示系](#7-名寄せ表示系) |

---

## 1. 環境構築・config.json系

### Q1-1：パソコンに Python をインストールしたくない／入っていない
- **解決策**：**Python インストール不要です！** [`SETUP_GUIDE.md`](SETUP_GUIDE.md) の **「ルート A：ブラウザ完結ルート」** を使い、同梱 `tools/config_builder.html` で設定を作って GitHub へアップロードし、GitHub Actions の `run_mode: demo` でクラウド実行してください。

### Q1-2：`config.json のJSON書式に誤りがあります`
- **原因**：手編集時の余分なカンマやダブルクォート閉じ忘れ。
- **解決策**：同梱の **`tools/config_builder.html`** を使って生成し直すと、構文エラーが起きなくなります。

### Q1-3：`安全運用ガード: 通知URLやトークンは config.json に書かず...`
- **原因**：Discord / Slack / ntfy.sh の URL を `config.json` の中に書いてしまいました。
- **解決策**：秘密情報保護のため、`config.json` には通知 ON/OFF だけを書き、URL は必ず GitHub リポジトリの **`Settings → Secrets and variables → Actions`**（`DISCORD_WEBHOOK_URL` / `SLACK_WEBHOOK_URL` / `NTFY_TOPIC_URL`）へ登録してください。

---

## 2. データ取得・HTML構造系

### Q2-1：`取得件数が0件でした` とエラーになる
1. **CSS セレクタ不一致・サイトリニューアル**：ブラウザで右クリック →「検証」→「Copy outerHTML」で最新 HTML をコピーし、[`AI_CUSTOMIZE_PROMPTS.md`](AI_CUSTOMIZE_PROMPTS.md) のプロンプト 1（または 8）で無料 AI に直してもらってください。
2. **JavaScript 動的描画サイト（SPA）**：「右クリック → ページのソースを表示」で価格の数字を検索し 1 件も出ない場合、JavaScript 描画ページです。まず同ページ内に `ld+json`（`type: "json_ld"`）や公開 CSV 版がないか確認してください。
3. **HTTP 403 / 429 ブロック**：対象サイトが自動取得を拒否しています。回避はせず、対象から外してください。

### Q2-2：`対象サイトの robots.txt により取得が禁止されています`
- **解決策**：サイト運営者の意向を尊重し、その URL は監視対象から外してください。

---

## 3. Googleスプレッドシート連携系

### Q3-1：`403 The caller does not have permission` / `SpreadsheetNotFound`
- **解決策**：出力先スプレッドシートの **「共有」** にサービスアカウントのメールアドレスを **「編集者」** で追加し、`OUTPUT_SPREADSHEET_ID` に余計なスラッシュや `/edit` が入っていないか確認してください。

### Q3-2：`Google Sheets API has not been used in project ... or it is disabled`
- **解決策**：Google Cloud コンソールで **`Google Sheets API`** と **`Google Drive API`** の両方を有効にし、2〜3 分待ってから再実行してください。

### Q3-3：`Could not deserialize key data` / `Invalid JSON`
- **解決策**：GitHub Secret `GOOGLE_CREDENTIALS_JSON` に、元の `.json` ファイルを `{` から最後の `}` まで 1 文字も欠かさず貼り付け直してください。

---

## 4. GitHub Actions 自動実行系

### Q4-1：予定時刻どおりに動かない
- **原因**：GitHub Actions 無料枠の `cron` は混雑時（特に毎時 00 分）に 5〜45 分遅延することがあります。
- **解決策**：`tools/config_builder.html` の「3. JST→UTC cron計算」で `17分` や `42分` など半端な分に設定してください。

### Q4-2：60 日経ったら自動更新が止まった
- **原因**：GitHub の仕様により、60 日間コミットがないリポジトリは定期実行が一時停止します。
- **解決策**：GitHub の **`Actions` タブ**（スマホアプリでも可）で **`Enable workflow`** を 1 回タップするだけで再開します。

---

## 5. 無料プッシュ通知系

### Q5-1：ntfy.sh / Discord / Slack に通知が来ない
1. まず GitHub Actions の **`Run workflow` → `run_mode: test_notify`** を実行してください。
2. テスト通知は届くのに普段届かない場合：初期設定では **`always_notify_summary: false`** のため、**「目標価格に到達した日」または「エラーが発生した日」だけ通知** します（うるさくしない設計）。毎日必ず通知を受け取りたい場合は `config.json` の `"always_notify_summary": true` にしてください。
3. テスト通知も失敗する場合：GitHub Secrets の名前（`NTFY_TOPIC_URL` / `DISCORD_WEBHOOK_URL` / `SLACK_WEBHOOK_URL`）のスペルと、`https://` から始まっているか確認してください。

---

## 6. スマホ手動更新ページ系

### Q6-1：`401 合言葉が違います`
- **解決策**：`tools/config_builder.html` の「2. 合言葉ハッシュ生成」で 64 文字ハッシュを作り直し、Cloudflare Workers または Vercel の `UPDATE_PASSWORD_HASH` を更新して **再デプロイ（Redeploy）** してください。

### Q6-2：`429 更新中または連続実行防止中です`
- **原因**：正常な安全動作（5 分クールダウン）です。表示された分数だけ待って再試行してください。

### Q6-3：`502 更新を開始できませんでした`
- **原因**：GitHub Fine-grained トークンの期限切れ、`Actions: Read and write` 権限漏れ、または `GITHUB_OWNER` / `GITHUB_REPO` のスペルミスです。トークンを再発行して環境変数を更新してください。
- ※ トークン管理をゼロにしたい場合は、**GitHub 公式スマホアプリの `Actions → Run workflow` 直起動** がもっとも手軽です。

---

## 7. 名寄せ・表示系

### Q7-1：同じ商品なのに別行に分かれる
- **解決策**：`全取得` タブの商品名リストをコピーし、[`AI_CUSTOMIZE_PROMPTS.md`](AI_CUSTOMIZE_PROMPTS.md) の **プロンプト 3** で `normalization` ルールを一括生成して `config.json` に貼ってください。

### Q7-2：価格推移の「30日推移（ミニグラフ）」が空欄
- **原因**：`SPARKLINE` 折れ線グラフは **2 日分以上** の履歴が溜まったタイミングで自動描画されます。初日は空欄が正常です。
