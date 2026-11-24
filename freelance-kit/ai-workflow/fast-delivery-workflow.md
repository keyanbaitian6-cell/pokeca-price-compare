# 生成AI活用・短納期納品ワークフロー（作業時間を1/5にする実戦手順）

通常ゼロから組むと **15〜25時間** かかる「Web自動収集＋名寄せ＋Googleスプレッドシート自動整形＋クラウド定期実行＋マニュアル作成」を、**既存リポジトリの設計資産再利用 × 生成AI（課金APIキー不要）** により **実働3〜5時間（約1/5）** で高品質納品するための標準ワークフローです。

> **生成AIの使い方ルール（課金APIキー不要）**
> - コードの中に有料の外部AI API（OpenAI API等）を組み込むことはしません。
> - 受注者側が開発・テスト・文書作成の工程で、普段使っている生成AI（ChatGPT / Gemini / Claude のWeb画面、またはエディタ内のAIアシスタント）へ [`prompt-library.md`](./prompt-library.md) のプロンプトを貼り付けて超高速化します。
> - **秘密情報保護**：AIにプロンプトを貼る際、クライアントの個人情報・GoogleサービスアカウントJSON・GitHubトークン・合言葉の平文は**絶対に入力しない**こと（HTMLのサンプル断片やダミーデータのみを渡す）。

---

## 全体タイムライン比較（従来 vs AI活用ワークフロー）

| フェーズ | 従来の手作業 | 本ワークフロー（AI＋資産再利用） | 使用ツール／プロンプト |
| --- | ---: | ---: | --- |
| **Phase 0：応募前の技術調査＆提案** | 45〜60分 | **10分** | ブラウザDevTools + Prompt #1 |
| **Phase 1：要件定義・仕様合意** | 60〜90分 | **15分** | `hearing-sheet.md` + Prompt #2 |
| **Phase 2：収集＆名寄せ実装** | 5〜8時間 | **60〜90分** | 既存資産ひな型 + Prompt #3, #4 |
| **Phase 3：シート整形＆自動テスト** | 4〜6時間 | **45〜60分** | `google_output.py`流用 + Prompt #5, #6 |
| **Phase 4：クラウド設置＆マニュアル納品** | 3〜5時間 | **40〜60分** | Actions YAML流用 + Prompt #7 + 納品テンプレ |
| **合計（スタンダード3万円案件）** | **14〜21時間** | **約3.0〜4.5時間** | **実働 約1/5・時給6,500〜10,000円** |

---

## 再利用できる本リポジトリの「黄金パーツ」一覧

案件ごとにゼロから書かず、以下の実績済みモジュールをテンプレートとしてクライアント専用の別リポジトリへコピー＆AI改変して使います。

| 再利用パーツ（本リポジトリ内の設計元） | そのまま活かせる実運用ノウハウ |
| --- | --- |
| [`src/card_price_compare/http.py`](../../src/card_price_compare/http.py) | `build_session()`（429/5xx指数バックオフ＋`Retry-After`尊重）＋`PoliteRequester`（既定1秒間隔レート制限） |
| [`src/card_price_compare/normalize.py`](../../src/card_price_compare/normalize.py) | Unicode NFKC正規化、長いノイズ語から除去する安全設計、別名辞書、状態判定 |
| [`src/card_price_compare/cli.py`](../../src/card_price_compare/cli.py) | `--strict`（1サイト失敗時にシートを上書きしない保護）、JST固定タイムスタンプ、`utf-8-sig` CSV、`run_summary.json` |
| [`src/card_price_compare/google_output.py`](../../src/card_price_compare/google_output.py) | `batch_update`一括書式整形、差率/差額の二重強調、30日横型`SPARKLINE`＋非表示アーカイブ2層分離、`INDEX/MATCH/MAX`連動サマリー、保護エリア不干渉 |
| [`.github/workflows/manual-update.yml`](../../.github/workflows/manual-update.yml) | `TZ: Asia/Tokyo`、`concurrency`排他制御、`RUNNER_TEMP`への安全な一時認証ファイル書き出し、`workflow_dispatch`＋`schedule`併用 |
| [`vercel/api/update.js`](../../vercel/api/update.js) | SHA-256＋`crypto.timingSafeEqual`照合、同一オリジン確認、5分間クールダウン制御、Fine-grained PAT連携（スマホ1タップ更新オプション時） |

---

## フェーズ別・実戦手順

### Phase 0：応募前の「3分技術チェック」（赤字案件を入り口で排除）
1. 対象URLをブラウザで開き、ログイン不要＆CAPTCHA無しを確認。
2. ターミナルまたはDevToolsで静的HTMLかSPAかを1分で判定：
   ```bash
   curl -sL "https://対象URL" | grep -i "商品名の一部" | head -n 5
   ```
   - ヒットする → **静的HTML（requests + BeautifulSoup）** で高速実装可能。
   - ヒットしない（空の `<div id="root">` 等） → **SPA（Playwright）** を採用。
3. 対象サイトの `robots.txt` と利用規約を確認し、自動取得禁止がないかチェック。
4. [`prompt-library.md`](./prompt-library.md) の **Prompt #1** に案件文と上記3行メモを貼り、3分でパーソナライズ提案文を作成して応募！

### Phase 1：要件定義→「機械可読な仕様メモ」化（15分）
1. クライアントから返ってきた [`hearing-sheet.md`](../sales/hearing-sheet.md) の回答を **Prompt #2** に貼る。
2. 生成された「確定仕様・スコープ合意書」をクライアントへ送付し、テキスト合意＋購入（仮払い）を得る。
3. 同時に「収集対象のCSSセレクタ確認用HTML」をブラウザから1ページ分保存しておく（`tests/fixtures/site_a.html`）。

### Phase 2：コレクター＆名寄せのAI高速実装（60〜90分）
1. クライアント専用の作業ディレクトリ（別Gitリポジトリ）を作成し、`http.py`・`models.py` のひな型をコピー。
2. 保存したHTML断片（商品カード2〜3個分でOK。全HTMLは長すぎるので対象リスト周辺だけ抜粋）を **Prompt #3** へ渡し、`parse_*_html()` と `fetch_*_records()` を生成。
3. 複数サイト比較がある場合は、実取得した商品名10〜20件を **Prompt #4** へ渡し、NFKC正規化＋ノイズ除去＋別名辞書（`normalize.py`）を生成。
4. ローカル実行して `data/raw.csv` と `data/comparison.csv` を目視確認（2〜3分で1サイクル回る）。

### Phase 3：スプレッドシート自動整形＆オフライン単体テスト生成（45〜60分）
1. 合意したタブ構成・強調ルール（最安/最高値色・差率・差額・30日推移の有無）を **Prompt #5** へ渡し、`google_output.py` を生成。
2. 自分側のテスト用Googleスプレッドシートへ実際に出力し、見た目・列幅・数式・SPARKLINE・履歴降順を確認（このスクショまたは閲覧専用リンクをクライアントに中間確認してもらうと手戻りがゼロになる！）。
3. 実装済みコレクター＋保存済みHTMLフィクスチャを **Prompt #6** へ渡し、`pytest` テストコードを一括生成して `pytest -q` を全件PASSさせる。

### Phase 4：お客様環境デプロイ＆マニュアル自動生成（40〜60分）
1. **Prompt #7** に「今回の案件仕様・ファイル構成・保守ポイント（セレクタ一覧）」を渡し、[`delivery/client-manual-template.md`](../delivery/client-manual-template.md) ベースのお客様専用マニュアルを5分で完成させる。
2. お客様側の非公開GitHubリポジトリへコードを納品（またはZIP＋導入手順で共有）し、`GOOGLE_CREDENTIALS_JSON` シークレット設定後に GitHub Actions の **Run workflow** で初回疎通を実行。
3. スマホ手動更新オプションがある場合は、Vercelプロジェクト設定（`GITHUB_TOKEN` と `UPDATE_PASSWORD_HASH`）を行い、正しい合言葉・誤った合言葉・5分連打ガードの3パターンを疎通確認。
4. 納品完了連絡＋「検収5営業日のお願い＋将来のレイアウト変更時スポット保守のご案内」を送ってクローズ！

---

## 納品前・品質ゲートチェックリスト（10項目・全項目クリアで納品）

- [ ] **1. 秘密情報ゼロ確認**：リポジトリ内に認証JSON・合言葉平文・トークン・他案件のシートIDが1文字も入っていない（`git status` / `git diff` 確認）。
- [ ] **2. 既存テスト＆新規テスト全PASS**：`pytest`（＋Vercel使用時は `node --test`）がすべて成功する。
- [ ] **3. 0件エラー保護確認**：サイト構造変更や通信失敗で0件になった時、終了コード1になり既存シートを上書きしない（`--strict`）。
- [ ] **4. マナー配慮アクセス確認**：HTTPアクセス間隔が1秒以上、429/5xxリトライ付きになっている。
- [ ] **5. 日本時間（JST）統一確認**：GitHub Actions（UTC環境）でも `TZ=Asia/Tokyo` かつタイムスタンプが日本時間で記録される。
- [ ] **6. スプレッドシート実機表示確認**：文字切れ、桁崩れ、`#REF!`/`#N/A`数式エラー、書式残りがない。
- [ ] **7. Excel文字化け対策確認**：CSV出力がある場合、`utf-8-sig`（BOM付きUTF-8）になっている。
- [ ] **8. 無料枠消費見積もり確認**：1回のActions実行時間 × 月間実行回数 ≪ 2,000分（目安200分以下）であることを確認。
- [ ] **9. 対象サイト・保守ポイント記載**：マニュアルに「どのCSSセレクタを直せば復旧できるか」が明記されている。
- [ ] **10. クライアント検収手順の明示**：納品メッセージに「確認してほしいシートタブ3点」と「検収期限（5営業日）」を明記した。
