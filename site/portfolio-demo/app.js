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
    if (optTrend) selectedOptions.push('30日価格推移マトリクス＋SPARKLINE');
    if (optMobile) selectedOptions.push('スマホ1タップ手動更新ページ（合言葉認証）');
    if (optNotify) selectedOptions.push('条件アラート通知（メール/Slack/Discord）');
    if (optSupport) selectedOptions.push('納品後1ヶ月 軽微レイアウト修正保証');

    const siteText = sites === '1-2' ? '1〜2サイト' : sites === '3' ? '3サイト' : '4〜5サイト';
    const techText = tech === 'static' ? '通常Webページ中心' : 'JS描画（SPA）含む・または不明';
    const compareText = compare === 'list' ? 'サイト別一覧出力' : '複数サイト名寄せ・比較整形';

    const summaryText = [
      '【自動化システム 相談メモ（簡易見積もり結果）】',
      `・対象サイト数：${siteText}`,
      `・対象サイト方式：${techText}`,
      `・データ加工：${compareText}`,
      `・希望オプション：${selectedOptions.length ? selectedOptions.join(' / ') : 'なし'}`,
      `・想定プラン：${planName}（概算 ¥${minPrice.toLocaleString('ja-JP')}〜¥${maxPrice.toLocaleString('ja-JP')} / 納期 ${schedule}）`,
      '・対象URL（記入欄）：',
      '・取得したい項目（記入欄）：商品名、価格、在庫状況 など',
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
      title: 'STEP 01｜定時スケジュール＆スマホ1タップ起動',
      badge: 'GitHub Actions + Vercel無料枠',
      desc: '毎日決まった時間（例：朝8:00や夕方17:00）にクラウド上のLinux環境が自動起動します。さらにオプションのスマホ用更新ページを使えば、外出先から合言葉1つで即座に手動実行できます。',
      metas: [
        { label: '月額0円の根拠', text: 'GitHub Actions無料枠は月2,000分。1回2〜3分の毎日実行なら月約70〜90分（5%未満）で収まります。' },
        { label: '安全・連打対策', text: '合言葉はSHA-256ハッシュで照合し、5分間クールダウンと同時実行キュー制御で誤連打を防止します。' },
        { label: 'PC不要・警告ゼロ', text: '自分のPCをつけっぱなしにする必要なし。GAS特有の「未確認アプリ警告」も出ません。' },
        { label: '最小権限設計', text: 'GitHubトークンは対象リポジトリのActions起動権限のみに限定して安全に分離管理します。' },
      ],
      logLine: '[17:00:01 JST] Trigger accepted (schedule: 0 8 * * * UTC / ubuntu-latest)',
    },
    {
      title: 'STEP 02｜丁寧なWeb自動収集（静的＋SPA両対応）',
      badge: 'Python / BeautifulSoup / Playwright',
      desc: '通常のHTMLサイトは軽量なrequests＋BeautifulSoupで高速取得し、JavaScriptで後から描画される最新SPAサイトはヘッドレスChromium（Playwright）で確実に読み取ります。',
      metas: [
        { label: 'バリエーション展開', text: 'サイズ違い・状態違いなどのプルダウンや商品詳細JSONも個別レコードへ正確に展開可能です。' },
        { label: 'マナー配慮アクセス', text: 'リクエスト間隔を既定1秒以上に制御し、429/5xx応答には指数バックオフ＋Retry-Afterで穏やかに再試行します。' },
        { label: 'サイト独立エラー処理', text: '1サイトだけ一時障害が起きても、原因をログに記録しつつ他の設定と切り分けて追跡できます。' },
        { label: 'テスト可能性', text: '保存済みHTMLフィクスチャでオフライン単体テストを回せるため、改修時のデグレを防ぎます。' },
      ],
      logLine: '[17:00:48 JST] Fetched 3 sources politely (delay=1.0s, retries=0, total=148 rows)',
    },
    {
      title: 'STEP 03｜日本語名寄せ＆異常値セーフティ',
      badge: 'NFKC正規化 + Strict Guard',
      desc: '店舗ごとにバラバラな全角半角・記号・シリーズ接頭辞・型番を自動クレンジングして同一商品として突合します。万一サイト変更で0件になった場合は上書きを中断します。',
      metas: [
        { label: '表記揺れ吸収', text: 'Unicode NFKC正規化、長いノイズ語からの優先除去、別名辞書で店舗間の商品名ズレを解消します。' },
        { label: '状態・区分を厳格分離', text: '「新品/未開封」と「開封済/訳あり」を誤って混ぜず、片方のみ未記載なら「状態推定」と明示します。' },
        { label: '0件時データ保護', text: 'レイアウト変更で取得0件になった場合は異常終了させ、既存の正常なスプレッドシートを守ります。' },
        { label: '異常値レポート', text: '価格差20%超の商品や取得件数サマリーをJSONログへ出力し、運用の異変をすぐ検知できます。' },
      ],
      logLine: '[17:00:54 JST] Normalized & matched 72 multi-site items (strict guard: PASSED)',
    },
    {
      title: 'STEP 04｜Googleスプレッドシート自動整形',
      badge: 'Sheets API batch_update',
      desc: '値を入れるだけでなく、色分け・列幅・通貨書式・ヘッダー注釈・30日SPARKLINEミニグラフまでSheets APIのバッチ更新で毎回美しく再構築します。',
      metas: [
        { label: '一発で分かる強調', text: '最有利セルを緑、差率5%以上を赤太字、差額¥3,000以上を金太字にし、見落としをゼロにします。' },
        { label: '肥大化しない推移設計', text: '全履歴は非表示アーカイブに蓄積し、表示タブは1商品1行の30日横型マトリクス＋SPARKLINEで軽快に保ちます。' },
        { label: '手入力エリアの保護', text: 'サマリーの決まったセル範囲だけを更新し、お客様が書き込んだメモ欄を消さない設計が可能です。' },
        { label: '低APIコール数', text: 'batch_update集約により1実行約20コール程度に抑え、Google無料API枠内で安定稼働します。' },
      ],
      logLine: '[17:01:12 JST] Google Sheets batch_update complete (6 tabs formatted, 19 API calls)',
    },
    {
      title: 'STEP 05｜即判断できる閲覧・履歴管理・通知',
      badge: 'Google Sheets / Excel CSV / 任意通知',
      desc: '普段の業務で開くのは見慣れたGoogleスプレッドシートだけ。最新の更新履歴が最上段（2行目）に自動で積み上がり、必要に応じてメールやチャット通知も連携できます。',
      metas: [
        { label: '文字化けゼロCSV', text: 'Excelダウンロード用CSVもUTF-8 BOM付き（utf-8-sig）で出力でき、Windows Excelでも崩れません。' },
        { label: '履歴トレーサビリティ', text: '「いつ・何件取れて・エラーが何件か」を最大365回分自動記録し、サマリーと数式連動します。' },
        { label: '条件アラート拡張', text: '「目標価格を下回った」「在庫が復活した」時だけSlack・Discord・メールへ通知する拡張も可能です。' },
        { label: '保守しやすいドキュメント', text: '対象CSSセレクタと変更箇所をまとめた運用マニュアル付きで、長期運用も安心です。' },
      ],
      logLine: '[17:01:15 JST] DONE — Duration: 1m14s (Monthly free quota used: ~3.2%)',
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
      },

      hobby: {
        docTitle: 'トレカ・ホビー買取相場比較シート（サンプル）',
        modeLabel: '最高買取値（状態別名寄せ）',
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
      },

      stock: {
        docTitle: '仕入れ・人気アウトドアギア 在庫＆価格監視（サンプル）',
        modeLabel: '最安仕入＆在庫復活検知',
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
        archLogStatus.textContent = '模擬実行中...';
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
              archLogStatus.textContent = '模擬実行完了（消費枠 約2分 / ¥0）';
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

    function renderSpreadsheet() {
      const ds = state.datasets[state.genre];
      if (!ds || !sheetViewport) return;

      sheetDocTitle.textContent = ds.docTitle;
      sheetUpdatedMeta.textContent = `最終更新: ${ds.updatedAt} ｜ 取得エラー: 0件`;
      sheetControlsBar.hidden = state.sheetTab !== 'compare';

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
            <th>商品名（名寄せ後）</th>
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
            <th title="セル内SPARKLINE関数で自動描画（左＝古 → 右＝新）">30日推移</th>
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
      } else {
        const latest = ds.historyLog[0];
        const summaryHtml = `
          <div class="sheet-summary-wrap">
            <div class="sheet-kpi-grid">
              <div class="sheet-kpi-box"><span>全取得レコード</span><strong class="num">${latest.total} 件</strong></div>
              <div class="sheet-kpi-box"><span>比較行（2サイト以上）</span><strong class="num">${latest.matched} 件</strong></div>
              <div class="sheet-kpi-box"><span>単独掲載（分離表示）</span><strong class="num">${latest.single} 件</strong></div>
              <div class="sheet-kpi-box"><span>取得エラー</span><strong class="num" style="color:var(--brand);">${latest.errors} 件</strong></div>
            </div>
            <div class="sheet-table-scroll">
              <table class="sheet-table">
                <thead>
                  <tr>
                    <th>実行日時（最新が最上段）</th>
                    <th>起動トリガー</th>
                    <th class="is-num">全取得</th>
                    <th class="is-num">2サイト以上比較</th>
                    <th class="is-num">単独掲載</th>
                    <th class="is-num">取得エラー</th>
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
          setMobileStatus('401 Unauthorized：合言葉が一致しません（デモ用は demo2026 です）。', 'error');
          return;
        }

        const now = Date.now();
        if (state.mobileCooldownUntil > now) {
          const remainMin = Math.max(1, Math.ceil((state.mobileCooldownUntil - now) / 60000));
          setMobileStatus(`429 Too Many Requests：連続実行防止中です。約${remainMin}分後に再実行できます（上部の「初期状態に戻す」で即再テスト可）。`, 'warn');
          return;
        }

        const targetGenre = state.genre;
        state.mobileRunning = true;
        mobileTriggerBtn.disabled = true;
        clearMobileTimers();
        setMobileStatus('1/3 合言葉SHA-256照合OK → GitHub Actions ワークフローを起動しています...', '');

        const step2Timer = window.setTimeout(() => {
          setMobileStatus('2/3 対象サイトを巡回中（1秒間隔アクセス制御・名寄せ検証中）...', '');
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
          setMobileStatus('3/3 更新完了！スプレッドシートの価格・前回比・30日推移・更新履歴が反映されました（5分間の連打ガード有効）。', 'success');
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
