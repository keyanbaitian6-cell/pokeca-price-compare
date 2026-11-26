(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    const api = factory();
    root.ZeroRunDemo = api;
    if (typeof document !== 'undefined') {
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => api.initBrowserApp());
      } else {
        api.initBrowserApp();
      }
    }
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  /* ========================================================================
     1. Pure Calculation Engines (Exported for Automated Verification)
     ======================================================================== */

  function calculateRoi(params) {
    const minutesPerDay = Math.max(1, Number(params.minutesPerDay) || 30);
    const daysPerMonth = Math.max(1, Number(params.daysPerMonth) || 22);
    const hourlyWage = Math.max(500, Number(params.hourlyWage) || 1500);
    const planCost = Math.max(1000, Number(params.planCost) || 30000);

    const monthlyHours = (minutesPerDay * daysPerMonth) / 60;
    const monthlySavings = Math.round(monthlyHours * hourlyWage);
    const annualSavings = monthlySavings * 12;
    const paybackMonths = monthlySavings > 0 ? planCost / monthlySavings : 0;

    return {
      monthlyHours: Math.round(monthlyHours * 10) / 10,
      monthlySavings,
      annualSavings,
      paybackMonths: Math.round(paybackMonths * 10) / 10,
      firstYearSelf: planCost,
      firstYearOtherMin: 110000,
      firstYearOtherMax: 360000,
    };
  }

  function calculateEstimate(options) {
    const sites = options.sites || '3';
    const tech = options.tech || 'spa';
    const compare = options.compare || 'match';
    const optTrend = Boolean(options.optTrend);
    const optMobile = Boolean(options.optMobile);
    const optNotify = Boolean(options.optNotify);
    const optSupport = Boolean(options.optSupport);

    let minPrice = 15000;
    let schedule = '3〜4営業日';

    if (sites === '3') {
      minPrice += 5000;
      schedule = '5〜7営業日';
    } else if (sites === '4-5') {
      minPrice += 15000;
      schedule = '7〜10営業日';
    }

    if (tech === 'spa') {
      minPrice += 3000;
    }

    if (compare === 'match') {
      minPrice += 2000;
    }

    if (optTrend) {
      minPrice += 5000;
    }
    if (optMobile) {
      minPrice += 10000;
    }
    if (optNotify) {
      minPrice += 8000;
    }
    if (optSupport) {
      minPrice += 5000;
    }

    const maxPrice = minPrice + (minPrice >= 45000 ? 10000 : 5000);

    let planName = 'ライトプラン相当';
    if (minPrice >= 45000 || optMobile || sites === '4-5') {
      planName = 'カスタムプラン相当';
      schedule = minPrice >= 55000 ? '10〜14営業日' : '7〜10営業日';
    } else if (minPrice >= 25000) {
      planName = 'スタンダードプラン相当';
      schedule = '5〜7営業日';
    }

    const selectedOptions = [];
    if (optTrend) selectedOptions.push('30日間の価格推移表＋ミニ折れ線グラフ');
    if (optMobile) selectedOptions.push('スマホ1タップ手動更新ページ（合言葉認証・Cloudflare無料枠）');
    if (optNotify) selectedOptions.push('条件達成アラート通知（メール/Slack/Discord）');
    if (optSupport) selectedOptions.push('納品後1ヶ月 軽微レイアウト修正保証');

    const siteText = sites === '1-2' ? '1〜2サイト' : sites === '3' ? '3サイト' : '4〜5サイト';
    const techText = tech === 'static' ? 'シンプルな価格表・一覧ページ' : '最新EC・動きのあるサイト・よく分からない';
    const compareText = compare === 'list' ? 'サイトごとに一覧化するだけ' : '複数サイトの商品を並べて比較する';

    const summaryText = [
      '【自動化システム 相談メモ（かんたん見積もり結果）】',
      `・チェックしたいサイト数：${siteText}`,
      `・対象サイトのタイプ：${techText}`,
      `・シートの作り方：${compareText}`,
      `・追加したい機能：${selectedOptions.length ? selectedOptions.join(' / ') : 'なし'}`,
      `・想定プラン：${planName}（概算 ¥${minPrice.toLocaleString('ja-JP')}〜¥${maxPrice.toLocaleString('ja-JP')} / 納期 ${schedule}）`,
      '・対象URL（記入欄）：',
      '・集めたい項目（記入欄）：商品名、価格、在庫状況 など',
    ].join('\n');

    return {
      minPrice,
      maxPrice,
      planName,
      schedule,
      summaryText,
    };
  }

  /* ========================================================================
     2. Architecture Pipeline Specification Data
     ======================================================================== */

  const ARCH_STEPS = [
    {
      title: 'STEP 01｜毎日自動で起動（＋スマホ1タップ更新）',
      badge: '無料クラウド（GitHub Actions ＋ Cloudflare）',
      desc: '毎日決まった時間（例：朝8:00や夕方17:00）に無料のクラウド環境が自動で動き出します。オプションのスマホ専用ページを追加すれば、外出先から合言葉1つで「今すぐ更新」もできます。',
      metas: [
        { label: '月額0円・商用OKの理由', text: '自動実行に使うGitHub無料枠は月2,000分。1日1回2〜3分なら月約70〜90分（5%未満）で収まります。スマホ更新も商用OKのCloudflare無料枠で¥0です。' },
        { label: '安全な合言葉＆連打防止', text: '合言葉は暗号化して安全にチェック。さらに5分間の連打防止＆二重起動ブロックで誤操作を防ぎます。' },
        { label: 'PC不要・怖い警告なし', text: 'ご自身のパソコンをつけっぱなしにする必要なし。GAS特有の「未確認アプリ」の赤い警告画面も出ません。' },
        { label: '非公開環境で安心運用', text: 'お客様専用の非公開環境で管理するため、社外にデータや設定が漏れず、公開放置の自動停止も防げます。' },
      ],
      logLine: '[17:00:01] 毎日17:00のタイマーで無料クラウドが自動起動しました',
    },
    {
      title: 'STEP 02｜相手サイトへ配慮しながら自動収集',
      badge: '通常ページ＆最新ECサイト両対応',
      desc: 'シンプルな一覧ページは軽量に高速取得し、画面を開いたあとに価格が表示される最新ECサイトは自動ブラウザ（Playwright）で確実に読み取ります。',
      metas: [
        { label: 'サイズ・状態違いにも対応', text: 'プルダウン切り替えが必要な「新品・中古」「サイズ別」などの価格も1件ずつ分けて取得できます。' },
        { label: '迷惑をかけない丁寧な巡回', text: '1秒以上の間隔を空けて読み込み、相手サイトが混雑している時は自動で待ってから再挑戦します。' },
        { label: 'サイト別の原因追跡', text: '1サイトだけ一時的に繋がらない場合でも、どのサイトで何が起きたかを分かりやすく記録します。' },
        { label: '修正時も壊れにくいテスト', text: '保存データを使った自動テストを用意するため、将来の調整時に別の箇所が壊れるのを防ぎます。' },
      ],
      logLine: '[17:00:48] 対象3サイトから148件を1秒間隔で丁寧に取得しました（エラー0件）',
    },
    {
      title: 'STEP 03｜商品名ズレを統一＆失敗時のデータ保護',
      badge: '表記ゆれ自動整理 ＋ データ保護機能',
      desc: 'お店ごとにバラバラな全角・半角、「送料無料」などの余計な文字、型番を自動で整えて同じ商品を1行に揃えます。万一サイト変更で0件になった時は、今あるシートを消さずに停止します。',
      metas: [
        { label: 'バラバラの商品名を自動統一', text: '全角・半角の統一、販促ワードの除去、別名辞書によって、お店ごとの表記ズレをきれいに揃えます。' },
        { label: '新品・中古を混ぜない工夫', text: '状態違いを誤って同じ行に混ぜず、片方のお店だけ状態記載がない時は「状態推定」と注意表示します。' },
        { label: '失敗してもシートを守る', text: '相手サイトの変更で0件になった場合は自動で処理を止め、前回まで正常だったシートをそのまま保護します。' },
        { label: 'おかしな価格差もチェック', text: '価格差が20%を超える異常値や取得件数の変化をログへ記録し、運用の異変にすぐ気づけます。' },
      ],
      logLine: '[17:00:54] 表記ゆれを統一し、複数店舗で一致した72商品を整理（データ保護OK）',
    },
    {
      title: 'STEP 04｜Googleスプレッドシートを自動整形',
      badge: '色分け・価格差強調・30日グラフ',
      desc: 'ただ文字を貼り付けるだけでなく、色分け・見やすい列幅・¥表示・項目の説明メモ・30日ミニ折れ線グラフまで毎回自動で美しく整えます。',
      metas: [
        { label: 'パッと見で判断できる色分け', text: 'いちばん有利な価格を緑、差率5%以上を赤太字、差額¥3,000以上を金太字にして見落としを防ぎます。' },
        { label: 'ずっと重くならないグラフ設計', text: '過去全データは裏の保管用シートへ自動で貯め、見る画面は「1商品1行＋30日ミニグラフ」で軽快に保ちます。' },
        { label: '手入力メモ欄は消さない', text: 'お客様が自分でメモを書くセル範囲には触れない設計ができ、日々のメモと両立できます。' },
        { label: 'Googleの無料枠にたっぷり余裕', text: '1回の更新をまとめて書き込む工夫（約20回）により、Google公式APIの無料枠内で安定稼働します。' },
      ],
      logLine: '[17:01:12] Googleスプレッドシート6タブの色分け・30日グラフを更新しました',
    },
    {
      title: 'STEP 05｜開くだけですぐ判断＆履歴も自動保存',
      badge: 'スマホ閲覧・Excel出力・任意通知',
      desc: '普段のお仕事で開くのは見慣れたGoogleスプレッドシートだけ。最新の更新履歴がいちばん上に自動で残り、ご希望ならメールやチャット通知もつけられます。',
      metas: [
        { label: 'Excelでも文字化けしない', text: 'GoogleシートからExcel保存できるほか、Windows版Excelでも文字化けしないCSV出力にも対応できます。' },
        { label: '更新履歴を最大365回分記録', text: '「いつ・何件取れて・エラーが何件か」を自動記録。サマリー画面の数字も自動で連動します。' },
        { label: '条件達成の即時お知らせ', text: '「目標価格を下回った」「在庫が復活した」時だけメール・Slack・Discordへ通知する拡張も可能です。' },
        { label: '分かりやすい説明書付き', text: '操作方法と将来の修正箇所をまとめた説明書をお渡しするため、長く安心してお使いいただけます。' },
      ],
      logLine: '[17:01:15] 完了（処理時間 1分14秒 ／ 無料枠の月間使用目安 約3.2%）',
    },
  ];

  /* ========================================================================
     3. Anonymized Dummy Datasets (100% Fictitious Stores & Products)
     ======================================================================== */

  function createInitialDatasets() {
    return {
      ec: {
        docTitle: 'EC競合価格比較シート（ガジェット・家電 サンプル）',
        modeLabel: '最安競合（仕入・値付基準）',
        bestColLabel: '最安値',
        bestShopLabel: '最安ショップ',
        shops: ['ストアA', 'ストアB', 'ストアC'],
        higherIsBetter: false,
        updatedAt: '2026-11-24 17:02 JST',
        items: [
          {
            id: 'ec-1',
            name: 'ノイズキャンセリングイヤホン Pro X2',
            condition: '国内正規品・新品',
            prices: [24800, 27400, 26500],
            prevBest: 25600,
            sevenDayAgo: 26900,
            history: [26900, 26800, 26500, 26200, 25600, 24800],
            note: '',
          },
          {
            id: 'ec-2',
            name: 'ポータブル電源 1024Wh 急速充電モデル',
            condition: '新品未開封',
            prices: [89800, 84500, 91200],
            prevBest: 86000,
            sevenDayAgo: 88900,
            history: [88900, 88500, 87800, 86900, 86000, 84500],
            note: '',
          },
          {
            id: 'ec-3',
            name: '27インチ 4K USB-C モニター S27',
            condition: '新品未開封',
            prices: [44200, 42900, 46800],
            prevBest: 42900,
            sevenDayAgo: 44500,
            history: [44500, 44200, 43800, 43200, 42900, 42900],
            note: '',
          },
          {
            id: 'ec-4',
            name: 'メカニカルキーボード 75% 静音赤軸',
            condition: '日本語配列',
            prices: [15800, 16900, 14900],
            prevBest: 15200,
            sevenDayAgo: 15800,
            history: [15800, 15800, 15500, 15400, 15200, 14900],
            note: '状態推定',
          },
          {
            id: 'ec-5',
            name: 'ロボット掃除機 自動ゴミ収集ステーション付',
            condition: '国内正規品・新品',
            prices: [64800, 61200, 62500],
            prevBest: 59800,
            sevenDayAgo: 61500,
            history: [61500, 61000, 60200, 59800, 59800, 61200],
            note: '',
          },
          {
            id: 'ec-6',
            name: 'モバイルバッテリー 20000mAh 65W出力',
            condition: '新品未開封',
            prices: [7480, 7680, 7380],
            prevBest: 7380,
            sevenDayAgo: 7480,
            history: [7480, 7480, 7480, 7380, 7380, 7380],
            note: '',
          },
        ],
        historyLog: [
          { time: '2026-11-24 17:02', trigger: '定期 17:00', total: 148, matched: 72, single: 18, errors: 0 },
          { time: '2026-11-23 17:02', trigger: '定期 17:00', total: 146, matched: 71, single: 17, errors: 0 },
          { time: '2026-11-22 19:18', trigger: 'スマホ手動', total: 146, matched: 71, single: 17, errors: 0 },
          { time: '2026-11-22 17:02', trigger: '定期 17:00', total: 145, matched: 70, single: 18, errors: 0 },
        ],
        rawSamples: [
          {
            shop: 'ストアA',
            rawName: '【国内正規品・送料無料】ノイズキャンセリングイヤホン　Ｐｒｏ　Ｘ２（新品）',
            rawPrice: '24,800円(税込)',
            normalizedName: 'ノイズキャンセリングイヤホン Pro X2',
            condition: '国内正規品・新品',
            ruleNote: '全角→半角に揃え、「送料無料」などの余計な語をカット',
          },
          {
            shop: 'ストアB',
            rawName: '★即日発送★ ノイズキャンセリングイヤホン ProX2 国内正規 新品',
            rawPrice: '¥27,400',
            normalizedName: 'ノイズキャンセリングイヤホン Pro X2',
            condition: '国内正規品・新品',
            ruleNote: 'スペース差や呼び方違いを自動で同じ商品に統合',
          },
          {
            shop: 'ストアC',
            rawName: 'メカニカルキーボード 75％ 静音赤軸（記載省略）',
            rawPrice: '14,900円',
            normalizedName: 'メカニカルキーボード 75% 静音赤軸',
            condition: '日本語配列（状態推定）',
            ruleNote: '片方の店だけ状態記載なし → 「状態推定」の印を表示',
          },
        ],
      },

      hobby: {
        docTitle: 'トレカ・ホビー買取相場比較シート（サンプル）',
        modeLabel: '最高買取値（状態別に整理）',
        bestColLabel: '最高値',
        bestShopLabel: '最高値の店',
        shops: ['ショップα', 'ショップβ', 'ショップγ'],
        higherIsBetter: true,
        updatedAt: '2026-11-24 17:02 JST',
        items: [
          {
            id: 'hb-1',
            name: '蒼穹レジェンド 拡張BOX',
            condition: 'シュリンク有',
            prices: [18500, 16200, 17400],
            prevBest: 17800,
            sevenDayAgo: 16500,
            history: [16500, 16800, 17000, 17500, 17800, 18500],
            note: '',
          },
          {
            id: 'hb-2',
            name: 'アニバーサリーコレクション 限定BOX',
            condition: 'シュリンク有',
            prices: [132000, 137000, 134500],
            prevBest: 135000,
            sevenDayAgo: 131000,
            history: [131000, 132000, 133500, 134000, 135000, 137000],
            note: '',
          },
          {
            id: 'hb-3',
            name: 'スターライトフェス ハイクラスBOX',
            condition: 'シュリンク有',
            prices: [11800, 10200, 11500],
            prevBest: 12100,
            sevenDayAgo: 12400,
            history: [12400, 12300, 12200, 12100, 12100, 11800],
            note: '',
          },
          {
            id: 'hb-4',
            name: 'クロニクル・ゼロ 強化BOX',
            condition: 'シュリンク有',
            prices: [24500, 22800, 24000],
            prevBest: 24500,
            sevenDayAgo: 23200,
            history: [23200, 23500, 24000, 24200, 24500, 24500],
            note: '状態推定',
          },
          {
            id: 'hb-5',
            name: '蒼穹レジェンド 拡張BOX',
            condition: 'シュリンク無',
            prices: [13200, 12000, 12800],
            prevBest: 12900,
            sevenDayAgo: 12500,
            history: [12500, 12600, 12800, 12800, 12900, 13200],
            note: '',
          },
          {
            id: 'hb-6',
            name: 'スペシャルデッキセット DX',
            condition: '未開封',
            prices: [19200, 19200, 18900],
            prevBest: 19200,
            sevenDayAgo: 19000,
            history: [19000, 19000, 19100, 19200, 19200, 19200],
            note: '',
          },
        ],
        historyLog: [
          { time: '2026-11-24 17:02', trigger: '定期 17:00', total: 192, matched: 68, single: 24, errors: 0 },
          { time: '2026-11-23 17:02', trigger: '定期 17:00', total: 190, matched: 67, single: 25, errors: 0 },
          { time: '2026-11-22 17:02', trigger: '定期 17:00', total: 189, matched: 67, single: 24, errors: 0 },
        ],
        rawSamples: [
          {
            shop: 'ショップα',
            rawName: '【着払い対象外】シリーズA 拡張パック「蒼穹レジェンド」(S99a) シュリンク付きBOX',
            rawPrice: '18,500円',
            normalizedName: '蒼穹レジェンド 拡張BOX',
            condition: 'シュリンク有',
            ruleNote: '注記・型番(S99a)・括弧を自動でカットして整理',
          },
          {
            shop: 'ショップβ',
            rawName: '蒼穹レジェンド ＢＯＸ　シュリンク有り',
            rawPrice: '¥16,200',
            normalizedName: '蒼穹レジェンド 拡張BOX',
            condition: 'シュリンク有',
            ruleNote: '全角・半角を揃えて「シュリンク有」で同じ行に統合',
          },
          {
            shop: 'ショップγ',
            rawName: '蒼穹レジェンド BOX（シュリンク無し・ぺりぺり付）',
            rawPrice: '12,800円',
            normalizedName: '蒼穹レジェンド 拡張BOX',
            condition: 'シュリンク無',
            ruleNote: '「シュリンク有」と混ぜず、別の行として正しく分離',
          },
        ],
      },

      stock: {
        docTitle: '仕入れ・人気アウトドアギア 在庫＆価格監視（サンプル）',
        modeLabel: '最安仕入＆在庫復活チェック',
        bestColLabel: '最安値',
        bestShopLabel: '最安ショップ',
        shops: ['ショップX', 'ショップY', 'ショップZ'],
        higherIsBetter: false,
        updatedAt: '2026-11-24 17:02 JST',
        items: [
          {
            id: 'st-1',
            name: '軽量ソロテント UL-180（サンド）',
            condition: '在庫復活',
            prices: [36800, 41200, 39500],
            prevBest: 39500,
            sevenDayAgo: 41000,
            history: [41000, 41000, 40500, 39800, 39500, 36800],
            note: '在庫復活',
          },
          {
            id: 'st-2',
            name: 'チタン焚き火台 コンパクトM',
            condition: '在庫あり',
            prices: [14800, 13400, 14500],
            prevBest: 14200,
            sevenDayAgo: 14800,
            history: [14800, 14600, 14500, 14300, 14200, 13400],
            note: '',
          },
          {
            id: 'st-3',
            name: 'ダウンシュラフ 600FP 厳冬期モデル',
            condition: '残りわずか',
            prices: [48500, 52000, 49800],
            prevBest: 49800,
            sevenDayAgo: 52000,
            history: [52000, 51500, 51000, 50200, 49800, 48500],
            note: '',
          },
          {
            id: 'st-4',
            name: 'クーラーボックス ハード35L',
            condition: '在庫あり',
            prices: [28900, 27400, 29800],
            prevBest: 27400,
            sevenDayAgo: 28500,
            history: [28500, 28200, 27900, 27600, 27400, 27400],
            note: '',
          },
          {
            id: 'st-5',
            name: 'LEDランタン 充電式 1000lm',
            condition: '在庫あり',
            prices: [8600, 9200, 8800],
            prevBest: 8800,
            sevenDayAgo: 9100,
            history: [9100, 9000, 8900, 8800, 8800, 8600],
            note: '',
          },
        ],
        historyLog: [
          { time: '2026-11-24 17:02', trigger: '定期 17:00', total: 84, matched: 41, single: 9, errors: 0 },
          { time: '2026-11-23 17:02', trigger: '定期 17:00', total: 84, matched: 40, single: 10, errors: 0 },
          { time: '2026-11-22 17:02', trigger: '定期 17:00', total: 83, matched: 40, single: 10, errors: 0 },
        ],
        rawSamples: [
          {
            shop: 'ショップX',
            rawName: '【再入荷】軽量ソロテント ＵＬ−１８０／カラー：サンド [在庫あり]',
            rawPrice: '¥36,800',
            normalizedName: '軽量ソロテント UL-180（サンド）',
            condition: '在庫復活',
            ruleNote: '前回「売り切れ」→今回「在庫あり」を自動で検知',
          },
          {
            shop: 'ショップY',
            rawName: '軽量ソロテント UL180 (Sand) ※ポイント5倍対象',
            rawPrice: '41,200円',
            normalizedName: '軽量ソロテント UL-180（サンド）',
            condition: '在庫あり',
            ruleNote: 'ハイフン有無や英語・日本語の色名を同じ商品に統一',
          },
          {
            shop: 'ショップZ',
            rawName: 'ダウンシュラフ 600FP 厳冬期モデル（残り2点）',
            rawPrice: '49,800円',
            normalizedName: 'ダウンシュラフ 600FP 厳冬期モデル',
            condition: '残りわずか',
            ruleNote: '残り個数の表記から在庫ステータスを自動判定',
          },
        ],
      },
    };
  }

  function computeItemMetrics(item, dataset) {
    const validPrices = item.prices.filter((p) => typeof p === 'number' && p > 0);
    const maxP = Math.max.apply(null, validPrices);
    const minP = Math.min.apply(null, validPrices);
    const bestPrice = dataset.higherIsBetter ? maxP : minP;
    const spreadYen = maxP - minP;
    const spreadRate = maxP > 0 ? spreadYen / maxP : 0;
    const deltaPrev = bestPrice - item.prevBest;
    const delta7d = bestPrice - item.sevenDayAgo;

    const winningShops = [];
    item.prices.forEach((p, idx) => {
      if (p === bestPrice) {
        winningShops.push(dataset.shops[idx]);
      }
    });
    const bestShopText = winningShops.length === dataset.shops.length ? '3店同額' : winningShops.join('・');

    return {
      bestPrice,
      spreadYen,
      spreadRate,
      deltaPrev,
      delta7d,
      bestShopText,
    };
  }

  function formatYen(value) {
    return '¥' + Math.round(value).toLocaleString('ja-JP');
  }

  function formatSignedYen(value) {
    if (value === 0) return '±0';
    return (value > 0 ? '+¥' : '-¥') + Math.abs(Math.round(value)).toLocaleString('ja-JP');
  }

  function formatRate(rate) {
    return (rate * 100).toFixed(1) + '%';
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function buildSparklineSvg(values) {
    if (!Array.isArray(values) || values.length < 2) {
      return '';
    }
    const width = 96;
    const height = 24;
    const padX = 4;
    const padY = 4;
    const min = Math.min.apply(null, values);
    const max = Math.max.apply(null, values);
    const range = max - min || 1;
    const stepX = (width - padX * 2) / (values.length - 1);

    const points = values.map((val, i) => {
      const x = padX + i * stepX;
      const y = height - padY - ((val - min) / range) * (height - padY * 2);
      return [x.toFixed(1), y.toFixed(1)];
    });

    const polyline = points.map((pt) => pt.join(',')).join(' ');
    const last = points[points.length - 1];
    const diff = values[values.length - 1] - values[0];
    const stroke = diff > 0 ? '#137333' : diff < 0 ? '#175cd3' : '#687385';

    return (
      `<svg class="sparkline-svg" viewBox="0 0 ${width} ${height}" aria-label="30日推移グラフ">` +
      `<polyline fill="none" stroke="${stroke}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" points="${polyline}"/>` +
      `<circle cx="${last[0]}" cy="${last[1]}" r="2.6" fill="${stroke}"/>` +
      '</svg>'
    );
  }

  /* ========================================================================
     4. Browser Controller
     ======================================================================== */

  function initBrowserApp() {
    const state = {
      datasets: createInitialDatasets(),
      genre: 'ec',
      sheetTab: 'compare',
      filter: 'all',
      sort: 'rateDesc',
      archStep: 0,
      archAnimating: false,
      mobileRunning: false,
      mobileCooldownUntil: 0,
      mobileTimers: [],
      freshItemIds: new Set(),
    };

    // --- Mobile Navigation Toggle ---
    const navToggle = document.getElementById('navToggle');
    const siteNav = document.getElementById('siteNav');
    if (navToggle && siteNav) {
      navToggle.addEventListener('click', () => {
        const isOpen = siteNav.classList.toggle('is-open');
        navToggle.setAttribute('aria-expanded', String(isOpen));
      });
      siteNav.querySelectorAll('a').forEach((link) => {
        link.addEventListener('click', () => {
          siteNav.classList.remove('is-open');
          navToggle.setAttribute('aria-expanded', 'false');
        });
      });
    }

    // --- ROI Calculator ---
    const roiMinutes = document.getElementById('roiMinutes');
    const roiDays = document.getElementById('roiDays');
    const roiHourly = document.getElementById('roiHourly');
    const roiPlanCost = document.getElementById('roiPlanCost');

    function renderRoi() {
      if (!roiMinutes || !roiDays || !roiHourly || !roiPlanCost) return;
      const result = calculateRoi({
        minutesPerDay: roiMinutes.value,
        daysPerMonth: roiDays.value,
        hourlyWage: roiHourly.value,
        planCost: roiPlanCost.value,
      });
      document.getElementById('roiMinutesVal').textContent = `${roiMinutes.value} 分/日`;
      document.getElementById('roiDaysVal').textContent = `${roiDays.value} 日/月`;
      document.getElementById('roiSavedHours').textContent = `${result.monthlyHours.toFixed(1)} 時間`;
      document.getElementById('roiAnnualSavings').textContent = formatYen(result.annualSavings);
      document.getElementById('roiPaybackText').textContent =
        result.paybackMonths <= 0.5
          ? '約 2週間以内で元が取れます'
          : `約 ${result.paybackMonths.toFixed(1)} ヶ月で元が取れます`;
      const firstYearSelfEl = document.getElementById('roiFirstYearSelf');
      const firstYearOtherEl = document.getElementById('roiFirstYearOther');
      if (firstYearSelfEl) firstYearSelfEl.textContent = formatYen(result.firstYearSelf);
      if (firstYearOtherEl) {
        firstYearOtherEl.textContent = `${formatYen(result.firstYearOtherMin)}〜${formatYen(result.firstYearOtherMax)}`;
      }
    }

    [roiMinutes, roiDays, roiHourly, roiPlanCost].forEach((el) => {
      if (el) el.addEventListener('input', renderRoi);
    });
    renderRoi();

    // --- Architecture Visualizer ---
    const archStepBtns = Array.from(document.querySelectorAll('[data-arch-step]'));
    const runArchDemoBtn = document.getElementById('runArchDemoBtn');
    const archLogStatus = document.getElementById('archLogStatus');
    const archLogBody = document.getElementById('archLogBody');

    function renderArchDetail(stepIndex, logLimit) {
      const step = ARCH_STEPS[stepIndex] || ARCH_STEPS[0];
      archStepBtns.forEach((btn, idx) => {
        const active = idx === stepIndex;
        btn.classList.toggle('is-active', active);
        btn.setAttribute('aria-selected', String(active));
      });
      document.getElementById('archDetailTitle').textContent = step.title;
      document.getElementById('archDetailBadge').textContent = step.badge;
      document.getElementById('archDetailDesc').textContent = step.desc;
      document.getElementById('archMetaList').innerHTML = step.metas
        .map(
          (m) =>
            `<li class="arch-meta-item"><strong>${escapeHtml(m.label)}</strong><span>${escapeHtml(m.text)}</span></li>`
        )
        .join('');

      const count = typeof logLimit === 'number' ? logLimit : ARCH_STEPS.length;
      archLogBody.innerHTML = ARCH_STEPS.slice(0, count)
        .map((s, idx) => {
          const isFinal = idx === ARCH_STEPS.length - 1;
          const parts = s.logLine.split('] ');
          const timePart = parts[0] + ']';
          const msgPart = parts.slice(1).join('] ');
          return (
            `<li class="arch-log-line">` +
            `<span class="arch-log-time">${escapeHtml(timePart)}</span>` +
            `<span class="${isFinal ? 'arch-log-ok' : ''}">${escapeHtml(msgPart)}</span>` +
            `</li>`
          );
        })
        .join('');
    }

    archStepBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        if (state.archAnimating) return;
        state.archStep = Number(btn.getAttribute('data-arch-step')) || 0;
        renderArchDetail(state.archStep, ARCH_STEPS.length);
      });
    });

    if (runArchDemoBtn) {
      runArchDemoBtn.addEventListener('click', () => {
        if (state.archAnimating) return;
        state.archAnimating = true;
        runArchDemoBtn.disabled = true;
        archLogStatus.textContent = '自動更新の流れを再生中...';
        let current = 0;

        function advance() {
          archStepBtns.forEach((b, i) => b.classList.toggle('is-running', i <= current));
          state.archStep = current;
          renderArchDetail(current, current + 1);
          current += 1;
          if (current < ARCH_STEPS.length) {
            window.setTimeout(advance, 800);
          } else {
            window.setTimeout(() => {
              archStepBtns.forEach((b) => b.classList.remove('is-running'));
              archLogStatus.textContent = '再生完了（処理目安 約2分 ／ ¥0）';
              state.archAnimating = false;
              runArchDemoBtn.disabled = false;
            }, 650);
          }
        }
        advance();
      });
    }
    renderArchDetail(0, ARCH_STEPS.length);

    // --- Live Spreadsheet Demo ---
    const sheetViewport = document.getElementById('sheetViewport');
    const sheetControlsBar = document.getElementById('sheetControlsBar');
    const sheetDocTitle = document.getElementById('sheetDocTitle');
    const sheetUpdatedMeta = document.getElementById('sheetUpdatedMeta');
    const sheetSortSelect = document.getElementById('sheetSortSelect');
    const sheetLegend = document.getElementById('sheetLegend');

    function renderSpreadsheet() {
      const ds = state.datasets[state.genre];
      if (!ds || !sheetViewport) return;

      sheetDocTitle.textContent = ds.docTitle;
      sheetUpdatedMeta.textContent = `最終更新: ${ds.updatedAt} ｜ 取得エラー: 0件`;
      sheetControlsBar.hidden = state.sheetTab !== 'compare';

      if (sheetLegend) {
        if (state.sheetTab === 'compare') {
          sheetLegend.innerHTML =
            '<span class="legend-item"><span class="legend-swatch" style="background:#c6efce;border:1px solid #82c997;"></span>いちばん有利な価格（緑）</span>' +
            '<span class="legend-item"><span class="legend-swatch" style="background:#b42318;"></span>差率5%以上（赤太字）</span>' +
            '<span class="legend-item"><span class="legend-swatch" style="background:#a66900;"></span>差額¥3,000以上（金太字）</span>' +
            '<span class="legend-item"><span class="legend-swatch" style="background:#fff2cc;border:1px solid #e6c66a;"></span>状態推定などの注意</span>' +
            '<span class="legend-scroll-cue">← 横スクロールで全列を表示 →</span>';
        } else if (state.sheetTab === 'trend') {
          sheetLegend.innerHTML =
            '<span class="legend-item"><span class="legend-swatch" style="background:#137333;"></span>前回比・7日前比の上昇（緑）</span>' +
            '<span class="legend-item"><span class="legend-swatch" style="background:#175cd3;"></span>下落（青）</span>' +
            '<span class="legend-item">1商品1行で見やすく表示（過去全データは裏シートに自動保管）</span>' +
            '<span class="legend-scroll-cue">← 横スクロールで過去日付列を表示 →</span>';
        } else if (state.sheetTab === 'beforeAfter') {
          sheetLegend.innerHTML =
            '<span class="legend-item"><span class="legend-swatch" style="background:#fffaf5;border:1px solid #e8cfa0;"></span>整形前：お店ごとのバラバラな表記</span>' +
            '<span class="legend-item"><span class="legend-swatch" style="background:#f2fbf7;border:1px solid #82c997;"></span>整形後：全角・半角＆状態まで自動整理</span>' +
            '<span class="legend-scroll-cue">← 横スクロールで自動整理の理由を確認 →</span>';
        } else {
          sheetLegend.innerHTML =
            '<span class="legend-item"><span class="legend-swatch" style="background:#e8f5f0;border:1px solid #82c997;"></span>最新の実行履歴が常にいちばん上（最大365回分）</span>' +
            '<span class="legend-item">エラー時は前回までのデータを守って停止</span>';
        }
      }

      if (state.sheetTab === 'compare') {
        let rows = ds.items.map((item) => ({
          item,
          metrics: computeItemMetrics(item, ds),
        }));

        if (state.filter === 'highRate') {
          rows = rows.filter((r) => r.metrics.spreadRate >= 0.05);
        } else if (state.filter === 'highYen') {
          rows = rows.filter((r) => r.metrics.spreadYen >= 3000);
        } else if (state.filter === 'moved') {
          rows = rows.filter((r) => r.metrics.deltaPrev !== 0);
        }

        if (state.sort === 'rateDesc') {
          rows.sort((a, b) => b.metrics.spreadRate - a.metrics.spreadRate);
        } else if (state.sort === 'yenDesc') {
          rows.sort((a, b) => b.metrics.spreadYen - a.metrics.spreadYen);
        } else if (state.sort === 'deltaDesc') {
          rows.sort((a, b) => Math.abs(b.metrics.deltaPrev) - Math.abs(a.metrics.deltaPrev));
        }

        const headerHtml = `
          <tr>
            <th>商品名（表記統一後）</th>
            <th>状態</th>
            <th class="is-num">${escapeHtml(ds.bestColLabel)}</th>
            <th class="is-num" title="前回更新時との差額（上昇=緑、下落=青）">前回比</th>
            <th>${escapeHtml(ds.bestShopLabel)}</th>
            <th class="is-num" title="差率 = (最高値 - 最安値) ÷ 最高値。5%以上を赤太字で強調">差率</th>
            <th class="is-num" title="差額 = 最高値 - 最安値。¥3,000以上を金太字で強調">差額</th>
            ${ds.shops.map((s) => `<th class="is-num">${escapeHtml(s)}</th>`).join('')}
            <th title="一部店舗で状態記載が省略された場合などに自動表示">注意</th>
          </tr>
        `;

        const bodyHtml = rows.length
          ? rows
              .map(({ item, metrics }) => {
                const deltaClass =
                  metrics.deltaPrev > 0
                    ? 'cell-delta-up'
                    : metrics.deltaPrev < 0
                    ? 'cell-delta-down'
                    : 'cell-delta-flat';
                const rateClass = metrics.spreadRate >= 0.05 ? 'cell-rate-high' : '';
                const yenClass = metrics.spreadYen >= 3000 ? 'cell-yen-high' : '';
                const freshClass = state.freshItemIds.has(item.id) ? 'is-fresh-row' : '';
                const noteCell = item.note
                  ? `<span class="${item.note === '在庫復活' ? 'cell-status-ok' : 'cell-warn-badge'}">${escapeHtml(item.note)}</span>`
                  : '';

                return `
                  <tr class="${freshClass}">
                    <td class="cell-product" title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</td>
                    <td>${escapeHtml(item.condition)}</td>
                    <td class="is-num num"><strong>${formatYen(metrics.bestPrice)}</strong></td>
                    <td class="is-num num ${deltaClass}">${formatSignedYen(metrics.deltaPrev)}</td>
                    <td>${escapeHtml(metrics.bestShopText)}</td>
                    <td class="is-num num ${rateClass}">${formatRate(metrics.spreadRate)}</td>
                    <td class="is-num num ${yenClass}">${formatYen(metrics.spreadYen)}</td>
                    ${item.prices
                      .map((p) => {
                        const isBest = p === metrics.bestPrice;
                        return `<td class="is-num num ${isBest ? 'cell-best-price' : ''}">${formatYen(p)}</td>`;
                      })
                      .join('')}
                    <td>${noteCell}</td>
                  </tr>
                `;
              })
              .join('')
          : `<tr><td colspan="11" style="text-align:center;padding:24px;color:var(--ink-muted);">条件に一致する行はありません。フィルタを「すべて表示」に戻してください。</td></tr>`;

        sheetViewport.innerHTML = `<div class="sheet-table-scroll"><table class="sheet-table"><thead>${headerHtml}</thead><tbody>${bodyHtml}</tbody></table></div>`;
      } else if (state.sheetTab === 'trend') {
        const dates = ['最新', '1日前', '3日前', '5日前', '7日前'];
        const rows = ds.items
          .map((item) => ({ item, metrics: computeItemMetrics(item, ds) }))
          .sort((a, b) => Math.abs(b.metrics.deltaPrev) - Math.abs(a.metrics.deltaPrev));

        const headerHtml = `
          <tr>
            <th>商品名</th>
            <th class="is-num">最新${escapeHtml(ds.bestColLabel)}</th>
            <th>${escapeHtml(ds.bestShopLabel)}</th>
            <th class="is-num">前回比</th>
            <th class="is-num">7日前比</th>
            <th title="セル内に自動で描かれる30日ミニ折れ線グラフ（左＝古 → 右＝新）">30日グラフ</th>
            ${dates.map((d) => `<th class="is-num">${d}</th>`).join('')}
          </tr>
        `;

        const bodyHtml = rows
          .map(({ item, metrics }) => {
            const dPrevClass =
              metrics.deltaPrev > 0 ? 'cell-delta-up' : metrics.deltaPrev < 0 ? 'cell-delta-down' : 'cell-delta-flat';
            const d7Class =
              metrics.delta7d > 0 ? 'cell-delta-up' : metrics.delta7d < 0 ? 'cell-delta-down' : 'cell-delta-flat';
            const h = item.history;
            const recentCols =
              h.length >= 6
                ? [h[h.length - 1], h[h.length - 2], h[h.length - 4], h[h.length - 5], h[0]]
                : h.slice(-5).reverse();
            return `
              <tr class="${state.freshItemIds.has(item.id) ? 'is-fresh-row' : ''}">
                <td class="cell-product">${escapeHtml(item.name)}</td>
                <td class="is-num num"><strong>${formatYen(metrics.bestPrice)}</strong></td>
                <td>${escapeHtml(metrics.bestShopText)}</td>
                <td class="is-num num ${dPrevClass}">${formatSignedYen(metrics.deltaPrev)}</td>
                <td class="is-num num ${d7Class}">${formatSignedYen(metrics.delta7d)}</td>
                <td>${buildSparklineSvg(item.history)}</td>
                ${recentCols.map((p) => `<td class="is-num num">${formatYen(p)}</td>`).join('')}
              </tr>
            `;
          })
          .join('');

        sheetViewport.innerHTML = `<div class="sheet-table-scroll"><table class="sheet-table"><thead>${headerHtml}</thead><tbody>${bodyHtml}</tbody></table></div>`;
      } else if (state.sheetTab === 'beforeAfter') {
        const samples = Array.isArray(ds.rawSamples) ? ds.rawSamples : [];
        const beforeAfterHtml = `
          <div class="sheet-ba-intro">
            <strong>なぜ「集めるだけ」のツールと違うの？</strong>
            <span>お店ごとにバラバラな全角・型番・販促文字・状態の書き方を自動で揃え、同じ商品だけを正確に横並び比較します。</span>
          </div>
          <div class="sheet-table-scroll">
            <table class="sheet-table">
              <thead>
                <tr>
                  <th>お店</th>
                  <th>整形前：サイト上の元の商品名（表記バラバラ）</th>
                  <th class="is-num">元の価格表記</th>
                  <th>整形後：統一した商品名</th>
                  <th>判定した状態</th>
                  <th>自動整理の内容</th>
                </tr>
              </thead>
              <tbody>
                ${samples
                  .map(
                    (row) => `
                      <tr>
                        <td><strong>${escapeHtml(row.shop)}</strong></td>
                        <td class="cell-raw-text">${escapeHtml(row.rawName)}</td>
                        <td class="is-num mono">${escapeHtml(row.rawPrice)}</td>
                        <td class="cell-after-name">${escapeHtml(row.normalizedName)}</td>
                        <td><span class="cell-status-ok">${escapeHtml(row.condition)}</span></td>
                        <td class="cell-rule-note">${escapeHtml(row.ruleNote)}</td>
                      </tr>
                    `
                  )
                  .join('')}
              </tbody>
            </table>
          </div>
        `;
        sheetViewport.innerHTML = beforeAfterHtml;
      } else {
        const latest = ds.historyLog[0];
        const summaryHtml = `
          <div class="sheet-summary-wrap">
            <div class="sheet-kpi-grid">
              <div class="sheet-kpi-box"><span>取得した全件数</span><strong class="num">${latest.total} 件</strong></div>
              <div class="sheet-kpi-box"><span>比較できた商品（2店以上）</span><strong class="num">${latest.matched} 件</strong></div>
              <div class="sheet-kpi-box"><span>1店のみ掲載（別タブ整理）</span><strong class="num">${latest.single} 件</strong></div>
              <div class="sheet-kpi-box"><span>取得エラー</span><strong class="num" style="color:var(--brand);">${latest.errors} 件</strong></div>
            </div>
            <div class="sheet-table-scroll">
              <table class="sheet-table">
                <thead>
                  <tr>
                    <th>更新した日時（最新がいちばん上）</th>
                    <th>更新のきっかけ</th>
                    <th class="is-num">全取得</th>
                    <th class="is-num">2店以上の比較</th>
                    <th class="is-num">1店のみ</th>
                    <th class="is-num">エラー</th>
                  </tr>
                </thead>
                <tbody>
                  ${ds.historyLog
                    .map(
                      (row, idx) => `
                        <tr class="${idx === 0 && state.freshItemIds.size > 0 ? 'is-fresh-row' : ''}">
                          <td class="mono">${escapeHtml(row.time)}</td>
                          <td>${escapeHtml(row.trigger)}</td>
                          <td class="is-num num">${row.total}</td>
                          <td class="is-num num">${row.matched}</td>
                          <td class="is-num num">${row.single}</td>
                          <td class="is-num num"><span class="cell-status-ok">${row.errors} 件</span></td>
                        </tr>
                      `
                    )
                    .join('')}
                </tbody>
              </table>
            </div>
          </div>
        `;
        sheetViewport.innerHTML = summaryHtml;
      }
    }

    // Genre switcher
    document.querySelectorAll('[data-genre]').forEach((btn) => {
      btn.addEventListener('click', () => {
        state.genre = btn.getAttribute('data-genre');
        state.freshItemIds.clear();
        document.querySelectorAll('[data-genre]').forEach((b) => b.classList.toggle('is-active', b === btn));
        renderSpreadsheet();
      });
    });

    // Sheet tab switcher
    document.querySelectorAll('[data-sheet-tab]').forEach((tab) => {
      tab.addEventListener('click', () => {
        state.sheetTab = tab.getAttribute('data-sheet-tab');
        document.querySelectorAll('[data-sheet-tab]').forEach((t) => {
          const active = t === tab;
          t.classList.toggle('is-active', active);
          t.setAttribute('aria-selected', String(active));
        });
        renderSpreadsheet();
      });
    });

    // Filter chips & sort
    document.querySelectorAll('[data-filter]').forEach((chip) => {
      chip.addEventListener('click', () => {
        state.filter = chip.getAttribute('data-filter');
        document.querySelectorAll('[data-filter]').forEach((c) => c.classList.toggle('is-active', c === chip));
        renderSpreadsheet();
      });
    });

    if (sheetSortSelect) {
      sheetSortSelect.addEventListener('change', () => {
        state.sort = sheetSortSelect.value;
        renderSpreadsheet();
      });
    }

    // --- Smartphone 1-Tap Manual Updater Demo ---
    const mobileUpdateForm = document.getElementById('mobileUpdateForm');
    const demoPassphrase = document.getElementById('demoPassphrase');
    const mobileTriggerBtn = document.getElementById('mobileTriggerBtn');
    const mobileStatusBox = document.getElementById('mobileStatusBox');
    const wrongPassTestBtn = document.getElementById('wrongPassTestBtn');
    const resetDemoBtn = document.getElementById('resetDemoBtn');

    function setMobileStatus(text, tone) {
      if (!mobileStatusBox) return;
      mobileStatusBox.textContent = text;
      mobileStatusBox.className = 'mobile-status-box' + (tone ? ` is-${tone}` : '');
    }

    if (wrongPassTestBtn && demoPassphrase) {
      wrongPassTestBtn.addEventListener('click', () => {
        demoPassphrase.value = 'wrong-pass';
        setMobileStatus('誤った合言葉を入力しました。このままボタンを押すと拒否動作を確認できます。', 'warn');
      });
    }

    function clearMobileTimers() {
      state.mobileTimers.forEach((id) => window.clearTimeout(id));
      state.mobileTimers = [];
    }

    function formatJstStamp(date) {
      try {
        const parts = new Intl.DateTimeFormat('en-CA', {
          timeZone: 'Asia/Tokyo',
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          hour12: false,
        }).formatToParts(date);
        const map = Object.fromEntries(parts.map((p) => [p.type, p.value]));
        return `${map.year}-${map.month}-${map.day} ${map.hour}:${map.minute}`;
      } catch (_err) {
        const pad = (n) => String(n).padStart(2, '0');
        return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
      }
    }

    if (resetDemoBtn) {
      resetDemoBtn.addEventListener('click', () => {
        clearMobileTimers();
        state.mobileRunning = false;
        if (mobileTriggerBtn) mobileTriggerBtn.disabled = false;
        state.datasets = createInitialDatasets();
        state.freshItemIds.clear();
        state.mobileCooldownUntil = 0;
        if (demoPassphrase) demoPassphrase.value = 'demo2026';
        setMobileStatus('デモデータを初期状態に戻しました。再度「今すぐ最新データを取得」をお試しいただけます。', '');
        renderSpreadsheet();
      });
    }

    if (mobileUpdateForm) {
      mobileUpdateForm.addEventListener('submit', (event) => {
        event.preventDefault();
        if (state.mobileRunning) return;

        const inputVal = (demoPassphrase?.value || '').trim();
        if (inputVal !== 'demo2026') {
          setMobileStatus('合言葉が違います（デモ用の合言葉は demo2026 です）。', 'error');
          return;
        }

        const now = Date.now();
        if (state.mobileCooldownUntil > now) {
          const remainMin = Math.max(1, Math.ceil((state.mobileCooldownUntil - now) / 60000));
          setMobileStatus(`連打防止ガードが働いています。約${remainMin}分後に再実行できます（上部の「初期状態に戻す」で即テスト可）。`, 'warn');
          return;
        }

        const targetGenre = state.genre;
        state.mobileRunning = true;
        mobileTriggerBtn.disabled = true;
        clearMobileTimers();
        setMobileStatus('1/3 合言葉OK！無料クラウドの自動更新をスタートしています...', '');

        const step2Timer = window.setTimeout(() => {
          setMobileStatus('2/3 対象サイトを1秒間隔で丁寧にチェック中（商品名ズレを自動整理）...', '');
        }, 700);

        const step3Timer = window.setTimeout(() => {
          const ds = state.datasets[targetGenre];
          state.freshItemIds.clear();

          // Apply realistic fresh market moves to 2 items
          ds.items.slice(0, 2).forEach((item, idx) => {
            const oldMetrics = computeItemMetrics(item, ds);
            item.prevBest = oldMetrics.bestPrice;
            const delta = ds.higherIsBetter
              ? idx === 0 ? 1200 : -1500
              : idx === 0 ? -900 : -1800;
            const targetShop = idx === 0 ? 0 : 1;
            item.prices[targetShop] = Math.max(1000, item.prices[targetShop] + delta);
            const newMetrics = computeItemMetrics(item, ds);
            item.history = item.history.slice(1).concat(newMetrics.bestPrice);
            item.sevenDayAgo = item.history[0];
            state.freshItemIds.add(item.id);
          });

          const stamp = formatJstStamp(new Date());
          ds.updatedAt = `${stamp} JST`;
          ds.historyLog.unshift({
            time: stamp,
            trigger: 'スマホ手動（デモ）',
            total: ds.historyLog[0].total + 2,
            matched: ds.historyLog[0].matched + 1,
            single: ds.historyLog[0].single,
            errors: 0,
          });

          state.mobileTimers = [];
          state.mobileRunning = false;
          state.mobileCooldownUntil = Date.now() + 5 * 60 * 1000;
          mobileTriggerBtn.disabled = false;
          setMobileStatus('3/3 更新完了！シートの価格・前回比・30日グラフ・更新履歴が最新になりました（5分間の連打防止中）。', 'success');
          renderSpreadsheet();
        }, 1550);

        state.mobileTimers.push(step2Timer, step3Timer);
      });
    }

    renderSpreadsheet();

    // --- Quick Estimator ---
    const estSummaryText = document.getElementById('estSummaryText');
    const copySummaryBtn = document.getElementById('copySummaryBtn');
    const copyFeedback = document.getElementById('copyFeedback');

    function readEstimatorOptions() {
      const sites = document.querySelector('input[name="estSites"]:checked')?.value || '3';
      const tech = document.querySelector('input[name="estTech"]:checked')?.value || 'spa';
      const compare = document.querySelector('input[name="estCompare"]:checked')?.value || 'match';
      return {
        sites,
        tech,
        compare,
        optTrend: Boolean(document.getElementById('optTrend')?.checked),
        optMobile: Boolean(document.getElementById('optMobile')?.checked),
        optNotify: Boolean(document.getElementById('optNotify')?.checked),
        optSupport: Boolean(document.getElementById('optSupport')?.checked),
      };
    }

    function renderEstimator() {
      const est = calculateEstimate(readEstimatorOptions());
      document.getElementById('estPlanLabel').textContent = `おすすめ：${est.planName}`;
      document.getElementById('estPriceRange').textContent = `${formatYen(est.minPrice)} 〜 ${formatYen(est.maxPrice)}`;
      document.getElementById('estSchedule').textContent = est.schedule;
      if (estSummaryText) estSummaryText.value = est.summaryText;
    }

    document.querySelectorAll('#estimator input').forEach((input) => {
      input.addEventListener('change', () => {
        if (copyFeedback) copyFeedback.textContent = '';
        renderEstimator();
      });
    });

    // Plan shortcut buttons
    document.querySelectorAll('[data-select-plan]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const plan = btn.getAttribute('data-select-plan');
        const setRadio = (name, value) => {
          const el = document.querySelector(`input[name="${name}"][value="${value}"]`);
          if (el) el.checked = true;
        };
        if (plan === 'light') {
          setRadio('estSites', '1-2');
          setRadio('estTech', 'static');
          setRadio('estCompare', 'list');
          document.getElementById('optTrend').checked = false;
          document.getElementById('optMobile').checked = false;
          document.getElementById('optNotify').checked = false;
          document.getElementById('optSupport').checked = false;
        } else if (plan === 'standard') {
          setRadio('estSites', '3');
          setRadio('estTech', 'spa');
          setRadio('estCompare', 'match');
          document.getElementById('optTrend').checked = true;
          document.getElementById('optMobile').checked = false;
          document.getElementById('optNotify').checked = false;
          document.getElementById('optSupport').checked = false;
        } else {
          setRadio('estSites', '4-5');
          setRadio('estTech', 'spa');
          setRadio('estCompare', 'match');
          document.getElementById('optTrend').checked = true;
          document.getElementById('optMobile').checked = true;
          document.getElementById('optNotify').checked = true;
          document.getElementById('optSupport').checked = true;
        }
        if (copyFeedback) copyFeedback.textContent = '';
        renderEstimator();
      });
    });

    if (copySummaryBtn && estSummaryText) {
      copySummaryBtn.addEventListener('click', async () => {
        try {
          if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(estSummaryText.value);
          } else {
            estSummaryText.select();
            document.execCommand('copy');
          }
          copyFeedback.textContent = 'コピーしました！ココナラ・クラウドワークス・XのDMにそのまま貼り付けできます。';
        } catch (_err) {
          estSummaryText.select();
          copyFeedback.textContent = 'テキストを選択しました。Ctrl+C / Cmd+C でコピーしてください。';
        }
      });
    }

    renderEstimator();

    // --- Mobile Sticky Bottom CTA Bar ---
    const mobileStickyCta = document.getElementById('mobileStickyCta');
    const heroSection = document.getElementById('hero');
    const estimatorSection = document.getElementById('estimator');
    if (mobileStickyCta && heroSection && estimatorSection && 'IntersectionObserver' in window) {
      let heroVisible = true;
      let estimatorVisible = false;

      function syncStickyCta() {
        mobileStickyCta.hidden = heroVisible || estimatorVisible;
      }

      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.target === heroSection) heroVisible = entry.isIntersecting;
            if (entry.target === estimatorSection) estimatorVisible = entry.isIntersecting;
          });
          syncStickyCta();
        },
        { threshold: 0.12 }
      );
      observer.observe(heroSection);
      observer.observe(estimatorSection);
      syncStickyCta();
    }
  }

  return {
    ARCH_STEPS,
    calculateEstimate,
    calculateRoi,
    computeItemMetrics,
    createInitialDatasets,
    buildSparklineSvg,
    initBrowserApp,
  };
});
