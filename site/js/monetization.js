/**
 * トレカ損益ラボ — 収益化・広告・運営設定ファイル
 * ============================================================
 * 【収益化の始め方（APIキー・課金一切不要）】
 * 1. A8.net / もしもアフィリエイト / afb / Amazonアソシエイトに登録し、
 *    提携した案件のURLを下の AFFILIATE_OFFERS の `url` に貼り付けてください。
 * 2. `url` を設定した項目だけ自動でボタンが表示され、景品表示法（ステマ規制）対応の
 *    「PR（広告）」表記も自動で有効化されます。
 * 3. Google AdSense 審査通過後は ADSENSE_CONFIG.enabled を true にして
 *    clientId と各 slotId を入力するだけで広告枠が表示されます。
 *
 * 詳しい手順はリポジトリ直下の MONETIZATION_GUIDE.md を参照してください。
 */

export const SITE_CONFIG = {
  siteName: 'トレカ損益ラボ',
  siteTagline: 'ポケカ・トレカ売却＆投資の無料計算ツール集',
  siteUrl: 'https://keyanbaitian6-cell.github.io/pokeca-price-compare',
  operatorName: 'トレカ損益ラボ運営',
  xHandle: '', // 例: '@your_x_handle'（設定するとフッターとシェア文に反映）
  contactUrl: '', // 例: 'https://forms.gle/xxxxx'（GoogleフォームやXプロフィールURL）
  lastUpdated: '2026-11-26',
};

export const ADSENSE_CONFIG = {
  enabled: false, // 審査通過後に true へ変更
  clientId: '', // 例: 'ca-pub-1234567890123456'
  slots: {
    topBanner: '',
    midContent: '',
    bottomBanner: '',
  },
};

/**
 * 文脈連動アフィリエイト案件設定
 * ユーザーの計算結果（「買取店が得」「フリマが得」「PSA提出が得」等）に応じて
 * 最も成約率の高いカテゴリのカードを自動表示します。
 *
 * url が空文字（''）の間はアフィリエイトリンクを出さず、クリーンな実用ガイドのみ表示します。
 */
export const AFFILIATE_OFFERS = {
  buyback: [
    {
      title: 'トレカ専門の宅配買取でまとめて現金化',
      badge: '送料・査定無料',
      description: 'フリマの出品・値下げ交渉・発送トラブルをゼロに。BOXや高額シングルを自宅から箱に詰めて送るだけで査定できます。',
      ctaText: '宅配買取の査定をチェック',
      url: '', // ← A8.net / もしも等のトレカ宅配買取（トレトク・カイトリワールド等）のリンクを貼る
      provider: 'A8.net / もしもアフィリエイト等',
    },
    {
      title: 'まとめ売り・ノーマルカード込みの一括買取',
      badge: 'まとめ売り向き',
      description: 'フリマで1枚ずつ売ると送料負けするカードや余剰サプライも、専門買取なら一括で整理できます。',
      ctaText: '買取キャンペーンを見る',
      url: '', // ← 2つ目の買取ASPリンク
      provider: 'ASP案件枠',
    },
  ],

  supplies: [
    {
      title: 'フリマ発送トラブル防止・梱包スターターセット',
      badge: '評価アップ',
      description: '折れ・濡れ対策の硬質ローダー、OPP袋、プチプチ封筒をまとめ買いすると1発送あたり梱包費を30〜50円に圧縮できます。',
      ctaText: '定番の梱包資材を見る',
      url: '', // ← Amazonアソシエイト / Yahoo!ショッピング等のアフィリエイトリンク
      provider: 'Amazonアソシエイト等',
    },
    {
      title: '未開封BOX専用 UVカット保護ローダー',
      badge: 'シュリンク保護',
      description: '角潰れやシュリンク破れは買取価格を数千円下げます。長期保管・発送前の保護に定番の専用ケース。',
      ctaText: 'BOX保護ローダーを探す',
      url: '', // ← Amazonアソシエイト等のリンク
      provider: 'Amazonアソシエイト等',
    },
  ],

  psa: [
    {
      title: 'PSA提出の必須アイテム（カードセーバー1＋スリーブ）',
      badge: '提出規格対応',
      description: 'PSA公式が推奨するセミリジッドホルダー（カードセーバー1）。まとめ買いで1枚あたりの提出コストを抑えられます。',
      ctaText: 'PSA提出用サプライを見る',
      url: '', // ← Amazonアソシエイト等のリンク
      provider: 'Amazonアソシエイト等',
    },
    {
      title: 'PSA鑑定代行・梱包サポートサービス',
      badge: '初心者でも安心',
      description: '英語での申請手続きや保険手配が不安な場合は、国内の鑑定代行サービスを比較検討するのも一手です。',
      ctaText: '鑑定代行プランを確認する',
      url: '', // ← 鑑定代行 / トレカ系ASPリンク
      provider: 'ASP案件枠',
    },
  ],

  oripa: [
    {
      title: '還元率・総口数が明記されたオンラインオリパを比較',
      badge: '透明性重視',
      description: 'オリパを引くなら「総口数・残り口数・最低保証」が明示されている大手サイトを選ぶのが鉄則です。',
      ctaText: '大手オンラインオリパを見る',
      url: '', // ← オンラインオリパ系高単価ASPリンク（DOPA / Clove / 日本トレカセンター等）
      provider: '高単価ASP案件枠',
    },
    {
      title: '引き当てた高額カードをすぐ現金化したい場合',
      badge: '出口戦略',
      description: '相場が下がる前に宅配買取やフリマで利益確定すると、収支が安定します。',
      ctaText: '宅配買取の相場を見る',
      url: '', // ← トレカ買取ASPリンク
      provider: 'ASP案件枠',
    },
  ],
};

/**
 * 設定済みの有効なアフィリエイト案件が存在するか判定（ステマ規制のPR表記自動制御に使用）
 */
export function hasActiveAffiliateLinks() {
  return Object.values(AFFILIATE_OFFERS).some((list) =>
    list.some((offer) => typeof offer.url === 'string' && offer.url.trim().startsWith('http'))
  );
}

/**
 * 指定カテゴリの有効な案件を取得
 */
export function getActiveOffers(category) {
  const list = AFFILIATE_OFFERS[category] || [];
  return list.filter((offer) => typeof offer.url === 'string' && offer.url.trim().startsWith('http'));
}
