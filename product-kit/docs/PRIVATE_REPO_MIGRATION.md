# 収益防衛ガイド：公開リポジトリから Private リポジトリへの安全分離手順

現在、本リポジトリ（`keyanbaitian6-cell/pokeca-price-compare`）は **GitHub Pages で無料ツール・ライブデモを公開するため `PUBLIC`（公開）** に設定されています。  
有料デジタル商品の本格販売を開始するタイミングで、**「集客用の無料ライブデモ（公開）」と「有料商品本体（非公開）」をきれいに分離する設計と手順** をまとめます。

---

## 1. 分離後のベスト構成（公開 vs 非公開）

| リポジトリ | 公開設定 | 収容するもの | 役割 |
| --- | :---: | --- | --- |
| **既存：`pokeca-price-compare`** | **PUBLIC** | ・既存ポケカ運用コード（`src/card_price_compare/`, `vercel/` 等）<br>・既存無料Webツール（`site/*.html`, `site/market/`, `site/portfolio-demo/`）<br>・**公開ライブ体験デモ（`site/price-kit/`）** | 集客エンジン＆無料体験 LP（GitHub Pages で継続公開） |
| **新規：`price-monitor-kit-private`**（例） | **PRIVATE** | ・**`product-kit/` 一式**（`template/`, `scripts/`, `tests/`, `sales/`, `docs/`） | 有料商品本体・出荷ZIP生成・バージョン管理（外部非公開） |

> **ポイント**:
> - `site/price-kit/` は「購入前に触れるデモ（架空サンプルデータのみ）」なので **PUBLIC のまま残すのが最も成約率が高くなります**。
> - 一方、`product-kit/template/`（購入者配布コード・プロンプト集・`config_builder.html`）と `product-kit/sales/`（販売戦略・LP原稿）は **PRIVATE リポジトリへ移管** することで、無断取得・転載を防げます。

---

## 2. 安全に移行する 4 ステップ（データ消失ゼロ）

### STEP 1：ローカルで Private リポジトリ用のクリーンなパッケージを作成する
付属の補助スクリプトを使うと、`.venv/` や `dist/` などの一時ファイルを除外し、テスト＆ZIPビルドがそのまま動く独立フォルダを安全に生成できます。

```powershell
# 1. まず --dry-run でコピー対象を確認
product-kit\.venv\Scripts\python.exe product-kit\scripts\prepare_private_repo.py `
  --dest "C:\Users\keyan\works\price-monitor-kit-private" `
  --dry-run

# 2. 問題なければ実行（新規フォルダを作成し、git init・テスト・ZIP検証まで実行可能）
product-kit\.venv\Scripts\python.exe product-kit\scripts\prepare_private_repo.py `
  --dest "C:\Users\keyan\works\price-monitor-kit-private"
```

### STEP 2：GitHub に新しい「Private」リポジトリを作成して Push する
1. GitHub で右上の **「＋」→「New repository」** を開く。
2. Repository name に `price-monitor-kit-private` を入力し、**必ず `Private`（非公開）** を選択して作成（README や .gitignore の自動作成はオフ）。
3. PowerShell で作成したフォルダへ移動し、初回コミット＆Push：
   ```powershell
   cd C:\Users\keyan\works\price-monitor-kit-private
   git init -b main
   git add .
   git commit -m "Initialize private repository for Price Monitor Kit v2.0.0"
   git remote add origin https://github.com/keyanbaitian6-cell/price-monitor-kit-private.git
   git push -u origin main
   ```
4. Private リポジトリ側で仮想環境を作り、全テスト＆ZIP生成が独立して通ることを確認：
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r product-kit\template\requirements-dev.txt
   .\.venv\Scripts\python.exe -m pytest -v product-kit\template\tests product-kit\tests
   node --test product-kit\template\mobile_updater\test\*.test.js
   .\.venv\Scripts\python.exe product-kit\scripts\build_release_zip.py --version 2.0.0
   ```

### STEP 3：公開リポジトリ（`pokeca-price-compare`）から有料商品本体を取り除く
Private リポジトリへの Push と動作確認が **完全に終わってから**、公開リポジトリ側から `product-kit/` を削除します（`site/price-kit/` は残します！）。

```powershell
cd C:\Users\keyan\works\pokeca-price-compare
git rm -r product-kit/
git commit -m "Move paid product-kit sources to private repository (keep public demo at site/price-kit)"
git push origin main
```

### STEP 4：（任意）過去コミット履歴からも `product-kit/` を完全消去したい場合
STEP 3 だけでも通常閲覧（最新ツリー）からは見えなくなりますが、GitHub の過去コミット履歴（`96e95c9` 等）を辿れる状態まで完全に消したい場合は、以下の 2 択から選びます：

- **選択肢 A（手軽・推奨）**：
  - 公開リポジトリ側の最新ツリーから `product-kit/` を削除（STEP 3 のみ）し、今後のアップデート（v2.1 / v2.2 の追加プリセット・プロンプト拡充・改善）は **Private リポジトリでのみ開発・配布** する。既存リポジトリの履歴書き換えリスク（force-push による他環境とのズレ）を回避しつつ、商品価値は確実に Private 側へ集約できます。
- **選択肢 B（履歴から完全消去）**：
  - `git-filter-repo` を使って `product-kit/` の履歴を完全除去し、`git push --force origin main` を実行（その後 GitHub サポートへキャッシュ削除依頼）。※既存ポケカ運用ワークフローやローカルブランチの再同期が必要になるため、実施前に必ずリポジトリ全体のバックアップを取ってください。

---

## 3. （将来オプション）公開ライブデモの URL を完全中立化する
現在、ライブデモの URL は `https://keyanbaitian6-cell.github.io/pokeca-price-compare/price-kit/` です。  
ポケカ色（`pokeca-price-compare`）を完全に消した中立ブランド URL にしたい場合：

1. **Cloudflare Pages**（無料枠・商用利用 OK）にログイン。
2. リポジトリ `pokeca-price-compare` を接続し、**Build output directory** に `site/price-kit` を指定してデプロイ（ビルドコマンドは空欄）。
3. `https://price-monitor-kit.pages.dev` のような中立 URL が月額 0 円で発行されます！
