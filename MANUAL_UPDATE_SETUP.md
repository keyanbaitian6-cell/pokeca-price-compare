# Vercel版・スマホ用「価格表を更新」ページの設定

GitHub Actionsにより毎日13:42（日本時間）ごろに自動更新されるほか、Vercelのスマホ用Webページで正しい合言葉が入力された時にも手動で1回実行されます。Google Apps Scriptは使用しないため、Googleの未確認アプリ警告も表示されません。

## 1. 非公開GitHubリポジトリを作る

推奨リポジトリ名: `pokeca-price-compare`

GitHubへ再ログインした後、このフォルダを非公開リポジトリとして登録します。`.gitignore`により、生成CSV、ローカル環境、認証JSONは登録対象から除外されます。コミット前に `git status` で認証ファイルが含まれていないことを必ず確認してください。

## 2. Google認証JSONをGitHub Actions Secretへ登録する

非公開リポジトリの `Settings > Secrets and variables > Actions > New repository secret` を開き、次を登録します。

- Name: `GOOGLE_CREDENTIALS_JSON`
- Secret: 出力用GoogleサービスアカウントJSONのファイル内容全体

サービスアカウントには、出力先シートだけを編集者として共有します。collectの参照元シートは共有・編集しません。

## 3. 更新起動専用のGitHubトークンを用意する

GitHubの `Settings > Developer settings > Personal access tokens > Fine-grained tokens` で作成します。

- Repository access: `pokeca-price-compare` だけ
- Repository permissions: `Actions: Read and write`
- 有効期限: できるだけ短くし、期限を管理する

このトークンはVercelのEnvironment Variablesだけに保存し、HTML、Googleシート、GitHubリポジトリには書きません。

## 4. Vercelへ登録する

VercelでGitHubリポジトリ `pokeca-price-compare` をImportします。

1. Root Directoryを `vercel` にする
2. Framework Presetは `Other` のままにする
3. Environment Variablesを登録してからDeployする

## 5. Environment Variablesを登録する

Vercelの `Project Settings > Environment Variables` に次を登録します。Production、Preview、Developmentのうち、少なくともProductionを選びます。

| 変数 | 値 |
| --- | --- |
| `GITHUB_TOKEN` | 手順3で作成したトークン |
| `UPDATE_PASSWORD_HASH` | 更新用合言葉をSHA-256化した64桁の16進文字列 |

合言葉そのものではなくハッシュだけを保存します。PowerShellでハッシュを作成する場合は、画面や履歴へ合言葉を残さない方法を使用してください。

## 6. 公開する

VercelのDeploy完了後に発行された `https://...vercel.app` をスマホで開きます。ページの利用時にGoogleやGitHubへのログインは不要です。

## 7. 動作確認

1. Webページで正しい合言葉を入力する
2. GitHubの `Actions` タブで「ポケカ価格表を手動更新」が開始されたことを確認する
3. 完了後にGoogleシートの5タブ（サマリー／比較／単独掲載／全取得／更新履歴）を確認する
4. 「更新履歴」に新しい行が1行増えていることを確認する
5. 間違った合言葉と5分以内の連打が拒否されることを確認する

公開URLが確定したら、出力シートのサマリーに「価格表を手動更新」リンクを設置します。Vercelの環境変数を変更した場合は再デプロイします。
