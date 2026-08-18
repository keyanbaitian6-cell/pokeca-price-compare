# スマホ用「価格表を更新」ページの設定

この構成は自動スケジュールを作りません。スマホ用Webページで正しい合言葉が入力された時だけ、GitHub Actionsが1回実行されます。

## 1. 非公開GitHubリポジトリを作る

推奨リポジトリ名: `pokeca-price-compare`

GitHubへ再ログインした後、このフォルダを非公開リポジトリとして登録します。`.gitignore`により、生成CSV、ローカル環境、認証JSONは登録対象から除外されます。コミット前に `git status` で認証ファイルが含まれていないことを必ず確認してください。

## 2. Google認証JSONをGitHub Actions Secretへ登録する

非公開リポジトリの `Settings > Secrets and variables > Actions > New repository secret` を開き、次を登録します。

- Name: `GOOGLE_CREDENTIALS_JSON`
- Secret: 出力用GoogleサービスアカウントJSONのファイル内容全体

サービスアカウントには、出力先シートだけを編集者として共有します。collectの参照元シートは共有・編集しません。

## 3. 更新起動専用のGitHubトークンを作る

GitHubの `Settings > Developer settings > Personal access tokens > Fine-grained tokens` で作成します。

- Repository access: `pokeca-price-compare` だけ
- Repository permissions: `Actions: Read and write`
- 有効期限: できるだけ短くし、期限を管理する

このトークンはApps ScriptのScript Propertiesだけに保存し、HTMLやGoogleシートには書きません。

## 4. Apps Scriptへ3ファイルを登録する

出力先Googleシートを開き、`拡張機能 > Apps Script` を選びます。

1. `apps-script/Code.gs` をスクリプトへ貼り付ける
2. HTMLファイル `Index` を追加し、`apps-script/Index.html` を貼り付ける
3. プロジェクト設定でマニフェスト表示を有効にし、`apps-script/appsscript.json` の内容へ置き換える

## 5. Script Propertiesを登録する

Apps Scriptの `プロジェクトの設定 > スクリプト プロパティ` に次を登録します。

| プロパティ | 値 |
| --- | --- |
| `GITHUB_OWNER` | `keyanbaitian6-cell` |
| `GITHUB_REPO` | `pokeca-price-compare` |
| `GITHUB_TOKEN` | 手順3で作成したトークン |
| `UPDATE_PASSWORD` | 更新用の合言葉（他サービスで使っていないもの） |
| `WORKFLOW_FILE` | `manual-update.yml` |
| `WORKFLOW_REF` | `main` |
| `MIN_INTERVAL_SECONDS` | `300` |
| `OUTPUT_SPREADSHEET_ID` | `1N3mF4tIjuq8FC3JO5QnT2rPKPn-tu3I8lFLP8ZNysYI` |

## 6. Webアプリとして公開する

Apps Scriptの `デプロイ > 新しいデプロイ > ウェブアプリ` を選びます。

- 次のユーザーとして実行: 自分
- アクセスできるユーザー: 全員（匿名アクセスを含む設定）

初回はGitHub Actionsを起動するための外部通信だけを承認します。Webアプリ自体はGoogleシートを読み取らず、価格表は固定リンクから開きます。発行された `/exec` URLをスマホで開き、合言葉を入力してテストします。

アカウントの種類によって匿名公開を選べない場合は、`Googleアカウントを持つ全員` に変更します。その場合、利用者はGoogleへのログインが必要です。

## 7. 動作確認

1. Webページで正しい合言葉を入力する
2. GitHubの `Actions` タブで「ポケカ価格表を手動更新」が開始されたことを確認する
3. 完了後にGoogleシートの4タブを確認する
4. 「更新履歴」に新しい行が1行増えていることを確認する
5. 間違った合言葉と5分以内の連打が拒否されることを確認する

公開URLが確定したら、出力シートのサマリーに「価格表を手動更新」リンクを設置します。
