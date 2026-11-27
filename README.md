# ポケカ未開封BOX 買取価格比較（v2.0）

主要6店舗の公開買取価格表から未開封ポケモンカードBOXの価格を自動取得・名寄せし、**個人用の詳細比較Googleスプレッドシート**と、**完全店舗匿名の公開Web相場インデックス（GitHub Pages）**を日次更新します。元サイトへの購入・買取申込やログインは一切行いません。

- 公開Web相場インデックス（店舗匿名・日次更新）: <https://keyanbaitian6-cell.github.io/pokeca-price-compare/market/>
- 売却手取り計算ツール「トレカ損益ラボ」: <https://keyanbaitian6-cell.github.io/pokeca-price-compare/>
- 2026年 価格表ソース調査＆再構築設計書: [docs/PRICE_LIST_DEEP_RESEARCH.md](docs/PRICE_LIST_DEEP_RESEARCH.md)
- 対象サイト・名寄せ・運用判断の記録: [docs/DECISIONS.md](docs/DECISIONS.md)

## 取得元（稼働6店舗＋一時中断1店舗）

| コード | 店舗名 | 種別 | 取得URL |
|---|---|---|---|
| `homura` | 買取ホムラ | 稼働中（静的HTML） | <https://kaitori-homura.com/column/2026/10/21/pokemon-box-buyback-price-list/> |
| `tcgpro` | トレカプロ | 稼働中（静的HTML） | <https://tcgpro.co.jp/box-kaitori/> |
| `morimori` | 森森買取 | 稼働中（静的HTML） | <https://www.morimori-kaitori.jp/category/price-list/2401010>（ほかSV・S&S） |
| `runto` | runto | 稼働中（静的HTML） | <https://runto666.com/product-category/card/> |
| `rudeya` | 買取ルデヤ | 稼働中（静的HTML） | <https://kaitori-rudeya.com/category/detail/114> |
| `somurie` | 買取ソムリエ | 稼働中（Playwright） | <https://somurie-kaitori.com/products?category=2&subcategory=7> |
| `collect` | コレクト | **一時中断**（既定外） | <https://docs.google.com/spreadsheets/d/1uNtzhQBeiPmGR8rjqgwNdesCHbD4Nr6Y4ecZAjBE15g/htmlview> |

コレクトの参照元シートは読み取り専用です。スクリプトはこのIDをGoogle出力先として拒否します（再開時は `--sources` に `collect` を追加してください）。

## セットアップ

Python 3.10以上を使用します。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -e .
.venv/bin/python -m playwright install chromium
```

## 実行

```bash
python3 -m card_price_compare --web-market-json site/market/data/market_index.json
```

特定店舗のみで疎通確認する場合:

```bash
python3 -m card_price_compare --sources homura,tcgpro,morimori,rudeya
```

主な出力:

- `data/raw_prices.csv`: 取得した全レコード
- `data/box_comparison.csv`: 同一商品・同一シュリンク状態で比較したBOX価格（最高値・中央値・最安値・2位価格・差額・一致店数）
- `data/shrink_trend_history.csv`: ローカル実行時に蓄積するシュリンク有BOXの日次推移履歴
- `data/market_insights.json`: 店舗名を匿名化した市況分析結果
- `data/ai_prompts.md` / `data/ai_prompts.json`: 無料/Web版生成AIへそのまま貼れるX投稿・週次note用プロンプト＆下書き素材（API課金不要）
- `site/market/data/market_index.json`: 公開Web相場インデックス用の完全匿名集計JSON（特定店舗名・ドメイン混入を自動検査して遮断）
- `data/run_summary.json`: 取得件数、一致店舗数分布、価格差20%超の検査結果、地合い概要、サイト別エラー

外部サイトへアクセスせず保存済みCSVからプロンプト・公開JSONのみ再生成する場合:

```bash
python3 -m card_price_compare --from-local-data --output-dir data --web-market-json site/market/data/market_index.json
```

## Googleスプレッドシート出力

1. Google CloudでSheets APIとDrive APIを有効化し、サービスアカウントJSONを用意します。
2. 出力用スプレッドシートをサービスアカウントと共有して以下を実行します。

```bash
python3 -m pip install -r requirements-google.txt
python3 -m card_price_compare \
  --google-spreadsheet-id "出力先ID" \
  --google-credentials "/path/to/service-account.json" \
  --web-market-json "site/market/data/market_index.json"
```

出力タブ構成（タブ順）:

1. **サマリー**: 最新集計カウンター、手動更新ページへのリンク
2. **比較**: 2店舗以上が掲載しているシュリンク有BOXを差率降順で表示（`シリーズ`・`定価比`・`前回比`・稼働店舗の動的列・最高値ハイライト）
3. **シュリンク無比較**: シュリンク無の最高値・店舗別価格と同名シュリンク有BOXとの「有無差額」「有無差率」を可視化
4. **価格推移（シュリンク有）**: 1商品1行の横型マトリクス＋`SPARKLINE`30日推移（全期間生データは非表示の「推移データ（保管用）」へ自動保存）
5. **単独掲載**: 1店舗のみ掲載のBOXを買取価格降順で分離表示
6. **店舗条件**: 各店舗の取得状態・今回件数・送料条件・価格保証ルール・振込手数料・入金目安・公式URLを一覧化
7. **更新履歴**: 実行履歴を新しい順で記録（最大365回）
8. **全取得**: 取得した全レコード（元商品名・JAN・受付状態・URL確認用）
9. **発信プロンプト**: 特定店舗名を完全除外したX／note向けコピペ用プロンプト集

## 生成AI連携・収益化＆無料ツール連携

- X/note発信＆収益化ロードマップ: [docs/X_NOTE_MONETIZATION_PLAYBOOK.md](docs/X_NOTE_MONETIZATION_PLAYBOOK.md)
- 無料計算ツール集「トレカ損益ラボ」（`site/`）収益化ガイド: [MONETIZATION_GUIDE.md](MONETIZATION_GUIDE.md)

## 自動更新・手動更新

GitHub Actions（`.github/workflows/manual-update.yml`）が日次スケジュールおよびVercel手動更新ページ（[MANUAL_UPDATE_SETUP.md](MANUAL_UPDATE_SETUP.md)）から実行され、Googleスプレッドシートと `site/market/data/market_index.json` を同時更新します。更新成功後、`.github/workflows/deploy-pages.yml` が自動連鎖してGitHub Pages（`トレカ損益ラボ`＋`/market/`）を再公開します。

## 保守ポイント

- `collectors/homura.py`: `table` 列構造・`.hmr-hublist__ttl`・`.hmr-hublist__price`
- `collectors/tcgpro.py`: `li.kb-item[data-price]`・`data-q`・`data-date`
- `collectors/morimori.py`: サブカテゴリ `2401010`/`2401001`/`2401002` の先頭 `table`
- `collectors/rudeya.py`: `article.pgrid-card`・`.product-card-price-value`・`.product-card-stopped`
- `collectors/runto.py`: `li.product`・`.price`・`form.variations_form`
- `collectors/somurie.py`: `.ant-card`
- `normalize.py` / `catalog.py`: 表記揺れ別名・公式BOX定価・シリーズ定義
- `stores.py`: 店舗条件マスタ・公開禁止語リスト

