/* Public Interactive Showcase & Demo for Price Monitor Kit v2.0 */
(function () {
  'use strict';

  const GENRE_DATA = {
    electronics: {
      title: '家電・ガジェット最安値ウォッチ（デモ）',
      mode: 'lowest',
      modeLabel: '最安値比較モード（安く買う）',
      stores: ['ショップAlpha', 'ショップBeta', 'ショップGamma'],
      featuredIndex: 0,
      sliderMin: 38000,
      sliderMax: 46000,
      sliderStep: 500,
      defaultTarget: 42000,
      rows: [
        {
          name: 'Sony WH-1000XM5 ワイヤレスヘッドホン',
          condition: '新品',
          prices: [44800, 41200, 42900],
          prevBest: 42500,
          trend: [45200, 44900, 44500, 43800, 43200, 42900, 42500, 41200],
        },
        {
          name: 'Nintendo Switch 有機ELモデル ホワイト',
          condition: '新品',
          prices: [36980, 34800, 35500],
          prevBest: 35200,
          trend: [36900, 36800, 36200, 35900, 35800, 35500, 35200, 34800],
        },
        {
          name: 'Apple AirPods Pro 第2世代 USB-C',
          condition: '新品',
          prices: [37500, null, 35800],
          prevBest: 35800,
          trend: [38200, 37800, 37500, 36900, 36500, 36000, 35800, 35800],
        },
        {
          name: 'Logicool MX Master 3S ワイヤレスマウス',
          condition: '新品',
          prices: [16200, 14800, 15400],
          prevBest: 15100,
          trend: [16500, 16200, 15900, 15800, 15500, 15400, 15100, 14800],
        },
      ],
    },
    buyback: {
      title: '中古カメラ・レトロゲーム買取比較（デモ）',
      mode: 'highest',
      modeLabel: '最高値比較モード（高く売る）',
      stores: ['買取店A', '買取店B', '買取店C'],
      featuredIndex: 0,
      sliderMin: 110000,
      sliderMax: 135000,
      sliderStep: 1000,
      defaultTarget: 124000,
      rows: [
        {
          name: 'RICOH GR III コンパクトデジタルカメラ',
          condition: '中古美品',
          prices: [118000, 126500, 121000],
          prevBest: 123000,
          trend: [115000, 117000, 118500, 120000, 121000, 122500, 123000, 126500],
        },
        {
          name: 'FUJIFILM X100V シルバー',
          condition: '中古美品',
          prices: [172000, 168000, 179000],
          prevBest: 175000,
          trend: [168000, 169000, 171000, 172000, 174000, 174500, 175000, 179000],
        },
        {
          name: 'ゲームボーイアドバンスSP ファミコンカラー',
          condition: '箱説付',
          prices: [18500, 21800, 19400],
          prevBest: 20500,
          trend: [18000, 18500, 19000, 19500, 19800, 20200, 20500, 21800],
        },
        {
          name: 'スーパーファミコン ジュニア本体 完品',
          condition: '箱説付',
          prices: [14200, 15800, null],
          prevBest: 15800,
          trend: [14500, 14800, 15000, 15200, 15500, 15600, 15800, 15800],
        },
      ],
    },
    oshi: {
      title: 'スニーカー・推し活グッズ値下げ監視（デモ）',
      mode: 'lowest',
      modeLabel: '最安値比較モード（安く買う）',
      stores: ['公式ストア', 'セレクトA', 'リユースB'],
      featuredIndex: 0,
      sliderMin: 18000,
      sliderMax: 25000,
      sliderStep: 500,
      defaultTarget: 22000,
      rows: [
        {
          name: '限定スニーカー Air Retro Low 27cm',
          condition: '新品',
          prices: [24200, 22800, 21500],
          prevBest: 22400,
          trend: [25000, 24800, 24000, 23600, 23200, 22900, 22400, 21500],
        },
        {
          name: '1/7 スケールフィギュア 限定カラーVer.',
          condition: '未開封',
          prices: [19800, 18400, 18900],
          prevBest: 18900,
          trend: [20800, 20400, 19900, 19500, 19400, 19100, 18900, 18400],
        },
        {
          name: '推し活アクリルスタンド ライブ限定',
          condition: '新品',
          prices: [4200, 3980, null],
          prevBest: 4100,
          trend: [4500, 4400, 4300, 4250, 4200, 4150, 4100, 3980],
        },
      ],
    },
    tcg: {
      title: 'トレカBOX 汎用買取比較（匿名ダミーデモ）',
      mode: 'highest',
      modeLabel: '最高値比較モード（高く売る）',
      stores: ['ショップX', 'ショップY', 'ショップZ'],
      featuredIndex: 0,
      sliderMin: 10000,
      sliderMax: 16000,
      sliderStep: 500,
      defaultTarget: 13500,
      rows: [
        {
          name: '拡張パック サンプルA',
          condition: '未開封',
          prices: [13200, 14100, 12800],
          prevBest: 13400,
          trend: [12000, 12300, 12600, 12900, 13000, 13200, 13400, 14100],
        },
        {
          name: 'ハイクラスパック サンプルB',
          condition: '未開封',
          prices: [9800, 9200, 10400],
          prevBest: 10200,
          trend: [9200, 9400, 9500, 9700, 9900, 10000, 10200, 10400],
        },
        {
          name: 'スペシャルセット サンプルC',
          condition: '未開封',
          prices: [24500, 26800, 25200],
          prevBest: 26000,
          trend: [24000, 24500, 24900, 25200, 25500, 25800, 26000, 26800],
        },
      ],
    },
  };

  let activeGenreKey = 'electronics';
  let activeTabKey = 'compare';
  let currentTargetPrice = GENRE_DATA.electronics.defaultTarget;

  function fmtYen(n) {
    if (n === null || n === undefined) return '—';
    return '¥' + Number(n).toLocaleString('ja-JP');
  }

  function fmtDelta(n) {
    if (n === 0) return '±0';
    return (n > 0 ? '+¥' : '-¥') + Math.abs(n).toLocaleString('ja-JP');
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function computeRowMetrics(row, mode, stores, targetPriceForRow) {
    const valid = row.prices
      .map((price, idx) => ({ price, store: stores[idx] }))
      .filter((x) => x.price !== null);
    const vals = valid.map((x) => x.price);
    const minVal = Math.min(...vals);
    const maxVal = Math.max(...vals);
    const best = mode === 'lowest' ? minVal : maxVal;
    const bestStores = valid.filter((x) => x.price === best).map((x) => x.store).join('・');
    const spreadYen = vals.length >= 2 ? maxVal - minVal : null;
    const spreadRate = spreadYen !== null && maxVal > 0 ? spreadYen / maxVal : null;
    const delta = best - row.prevBest;
    let targetHit = false;
    if (targetPriceForRow !== null) {
      targetHit = mode === 'lowest' ? best <= targetPriceForRow : best >= targetPriceForRow;
    }
    return { best, bestStores, spreadYen, spreadRate, delta, targetHit };
  }

  function sparklineSvg(values) {
    const w = 112;
    const h = 28;
    const pad = 3;
    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = max - min || 1;
    const pts = values.map((v, i) => {
      const x = pad + (i * (w - pad * 2)) / (values.length - 1);
      const y = h - pad - ((v - min) * (h - pad * 2)) / span;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    });
    const last = pts[pts.length - 1].split(',');
    return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" role="img" aria-label="30日価格推移グラフ">
      <polyline fill="none" stroke="#0d6b53" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" points="${pts.join(' ')}" />
      <circle cx="${last[0]}" cy="${last[1]}" r="3" fill="#0d6b53" />
    </svg>`;
  }

  function renderDemo() {
    const genre = GENRE_DATA[activeGenreKey];
    const mode = genre.mode;
    const bestLabel = mode === 'lowest' ? '最安値' : '最高値';
    const bestStoreLabel = mode === 'lowest' ? '最安の店' : '最高値の店';

    document.getElementById('sheetTitle').textContent = genre.title;
    document.getElementById('modeIndicator').textContent = genre.modeLabel;

    // Update target slider info
    const featured = genre.rows[genre.featuredIndex];
    const featuredMetrics = computeRowMetrics(featured, mode, genre.stores, currentTargetPrice);
    document.getElementById('targetItemName').textContent = featured.name;
    document.getElementById('targetSliderVal').textContent =
      fmtYen(currentTargetPrice) + (mode === 'lowest' ? ' 以下で通知' : ' 以上で通知');

    // Update smartphone push preview
    const pushBox = document.getElementById('pushPreview');
    const pushTitle = document.getElementById('pushTitle');
    const pushBody = document.getElementById('pushBody');
    if (featuredMetrics.targetHit) {
      pushBox.classList.remove('is-idle');
      pushTitle.textContent = `🎯 目標価格達成 (1件) - ${genre.title}`;
      pushBody.textContent =
        `・${featured.name} (${featured.condition})\n` +
        `現在${bestLabel}: ${fmtYen(featuredMetrics.best)} [${featuredMetrics.bestStores}]\n` +
        `目標ライン: ${fmtYen(currentTargetPrice)} → 条件クリア！`;
    } else {
      pushBox.classList.add('is-idle');
      pushTitle.textContent = '（今は目標未達のため通知スキップ中）';
      pushBody.textContent =
        `現在の${bestLabel}は ${fmtYen(featuredMetrics.best)} です。\n` +
        `スライダーを動かして目標ラインに達すると、ここにスマホ通知プレビューが点灯します。`;
    }

    const container = document.getElementById('sheetBody');

    if (activeTabKey === 'compare') {
      const rowsHtml = genre.rows
        .map((row, idx) => {
          const tgt = idx === genre.featuredIndex ? currentTargetPrice : null;
          const m = computeRowMetrics(row, mode, genre.stores, tgt);
          const isFavorable = mode === 'lowest' ? m.delta < 0 : m.delta > 0;
          const deltaClass = m.delta === 0 ? 'delta-flat' : isFavorable ? 'delta-good' : 'delta-bad';
          const rateClass = m.spreadRate !== null && m.spreadRate >= 0.05 ? 'cell-rate-high' : '';
          const yenClass = m.spreadYen !== null && m.spreadYen >= 2000 ? 'cell-yen-high' : '';
          const storeCells = row.prices
            .map((p) => {
              const cls = p !== null && p === m.best ? 'r num cell-best' : 'r num';
              return `<td class="${cls}">${fmtYen(p)}</td>`;
            })
            .join('');
          const badge =
            tgt === null
              ? '<span class="badge-watch">—</span>'
              : m.targetHit
                ? '<span class="badge-hit">🎯 目標達成</span>'
                : '<span class="badge-watch">監視中</span>';

          return `<tr>
            <td><strong>${escapeHtml(row.name)}</strong></td>
            <td>${escapeHtml(row.condition)}</td>
            <td class="r num"><strong>${fmtYen(m.best)}</strong></td>
            <td class="r num ${deltaClass}">${fmtDelta(m.delta)}</td>
            <td>${escapeHtml(m.bestStores)}</td>
            <td class="r num ${rateClass}">${m.spreadRate !== null ? (m.spreadRate * 100).toFixed(1) + '%' : '—'}</td>
            <td class="r num ${yenClass}">${fmtYen(m.spreadYen)}</td>
            ${storeCells}
            <td>${badge}</td>
          </tr>`;
        })
        .join('');

      container.innerHTML = `<table class="sheet-table">
        <thead>
          <tr>
            <th>商品名</th>
            <th>状態</th>
            <th class="r">${bestLabel}</th>
            <th class="r">前回比</th>
            <th>${bestStoreLabel}</th>
            <th class="r">差率</th>
            <th class="r">差額</th>
            ${genre.stores.map((s) => `<th class="r">${escapeHtml(s)}</th>`).join('')}
            <th>目標判定</th>
          </tr>
        </thead>
        <tbody>${rowsHtml}</tbody>
      </table>`;
    } else if (activeTabKey === 'trend') {
      const rowsHtml = genre.rows
        .map((row) => {
          const m = computeRowMetrics(row, mode, genre.stores, null);
          const d7 = row.trend[row.trend.length - 1] - row.trend[0];
          const isFav = mode === 'lowest' ? d7 < 0 : d7 > 0;
          const d7Class = d7 === 0 ? 'delta-flat' : isFav ? 'delta-good' : 'delta-bad';
          return `<tr>
            <td><strong>${escapeHtml(row.name)}</strong></td>
            <td>${escapeHtml(row.condition)}</td>
            <td class="r num"><strong>${fmtYen(m.best)}</strong></td>
            <td>${escapeHtml(m.bestStores)}</td>
            <td class="r num ${d7Class}">${fmtDelta(d7)}</td>
            <td>${sparklineSvg(row.trend)}</td>
            <td class="r num">${fmtYen(row.trend[row.trend.length - 2])}</td>
            <td class="r num">${fmtYen(row.trend[0])}</td>
          </tr>`;
        })
        .join('');

      container.innerHTML = `<table class="sheet-table">
        <thead>
          <tr>
            <th>商品名</th>
            <th>状態</th>
            <th class="r">最新${bestLabel}</th>
            <th>${bestStoreLabel}</th>
            <th class="r">7日前比</th>
            <th>30日推移 (SPARKLINE)</th>
            <th class="r">前回記録</th>
            <th class="r">7日前</th>
          </tr>
        </thead>
        <tbody>${rowsHtml}</tbody>
      </table>`;
    } else if (activeTabKey === 'alerts') {
      const m = featuredMetrics;
      const diff = m.best - currentTargetPrice;
      container.innerHTML = `<table class="sheet-table">
        <thead>
          <tr>
            <th>判定</th>
            <th>監視商品名</th>
            <th>状態</th>
            <th class="r">目標価格</th>
            <th class="r">現在${bestLabel}</th>
            <th class="r">目標との差</th>
            <th>${bestStoreLabel}</th>
          </tr>
        </thead>
        <tbody>
          <tr style="${m.targetHit ? 'background:#fdf3df;' : ''}">
            <td>${m.targetHit ? '<span class="badge-hit">🎯 目標達成</span>' : '<span class="badge-watch">監視中</span>'}</td>
            <td><strong>${escapeHtml(featured.name)}</strong></td>
            <td>${escapeHtml(featured.condition)}</td>
            <td class="r num">${fmtYen(currentTargetPrice)}</td>
            <td class="r num"><strong>${fmtYen(m.best)}</strong></td>
            <td class="r num">${fmtDelta(diff)}</td>
            <td>${escapeHtml(m.bestStores)}</td>
          </tr>
        </tbody>
      </table>`;
    } else {
      const hitCount = featuredMetrics.targetHit ? 1 : 0;
      container.innerHTML = `<table class="sheet-table">
        <thead>
          <tr><th>サマリー項目</th><th>自動集計値（数式連動）</th></tr>
        </thead>
        <tbody>
          <tr><td><strong>最終更新</strong></td><td class="num">2026-11-26 17:17 (JST)</td></tr>
          <tr><td><strong>比較モード</strong></td><td>${escapeHtml(genre.modeLabel)}</td></tr>
          <tr><td><strong>監視サイト数</strong></td><td class="num">${genre.stores.length} サイト（${escapeHtml(genre.stores.join(' / '))}）</td></tr>
          <tr><td><strong>比較対象（2サイト以上）</strong></td><td class="num">${genre.rows.length} 商品</td></tr>
          <tr><td><strong>🎯 目標価格達成件数</strong></td><td class="num"><strong>${hitCount} 件</strong></td></tr>
          <tr><td><strong>取得エラー</strong></td><td class="num">0 件</td></tr>
          <tr><td><strong>無料プッシュ通知</strong></td><td>ntfy.sh / Discord / Slack 連携待機中</td></tr>
        </tbody>
      </table>`;
    }
  }

  function selectGenre(key) {
    activeGenreKey = key;
    const g = GENRE_DATA[key];
    currentTargetPrice = g.defaultTarget;
    const slider = document.getElementById('targetSlider');
    slider.min = String(g.sliderMin);
    slider.max = String(g.sliderMax);
    slider.step = String(g.sliderStep);
    slider.value = String(g.defaultTarget);

    document.querySelectorAll('.genre-btn').forEach((b) => {
      b.classList.toggle('is-active', b.dataset.genre === key);
    });
    renderDemo();
  }

  // Cost savings simulator
  function updateSavings() {
    const monthlyTool = Number(document.getElementById('simMonthly').value);
    const kitPrice = Number(document.getElementById('simKitPrice').value);
    document.getElementById('simMonthlyVal').textContent = fmtYen(monthlyTool) + ' / 月';
    document.getElementById('simKitPriceVal').textContent = fmtYen(kitPrice) + '（買い切り）';

    const yearlyCostOther = monthlyTool * 12;
    const savings1y = Math.max(0, yearlyCostOther - kitPrice);
    const paybackMonths = Math.max(1, Math.ceil(kitPrice / Math.max(monthlyTool, 1)));
    document.getElementById('simSavingsNum').textContent = `年間 ${fmtYen(savings1y)} お得`;
    document.getElementById('simSavingsMeta').textContent =
      `市販ツール（年 ${fmtYen(yearlyCostOther)}）と比べて約 ${paybackMonths} ヶ月で元が取れ、それ以降はずっと月額 ¥0 です。`;
  }

  // Quick config.json preview playground
  function updateConfigPlayground() {
    const mode = document.getElementById('pgMode').value;
    const item = document.getElementById('pgItem').value.trim() || 'Sony WH-1000XM5';
    const target = Number(document.getElementById('pgTarget').value) || 40000;
    const delay = Math.max(1.5, Number(document.getElementById('pgDelay').value) || 2.0);
    const sample = {
      project: {
        title: mode === 'lowest' ? 'マイ最安値ウォッチ' : 'マイ買取最高値比較',
        comparison_mode: mode,
      },
      safety: {
        request_delay_seconds: delay,
        max_pages_per_source: 5,
        respect_robots_txt: true,
      },
      notifications: {
        enabled: true,
        notify_on_target_hit: true,
        notify_on_error: true,
      },
      alerts: {
        targets: [{ item, condition: '新品', target_price_yen: target }],
      },
      sources: [
        {
          id: 'shop_a',
          label: '公開ショップA',
          type: 'json_ld',
          url: 'https://shop-a.example/item',
        },
      ],
    };
    document.getElementById('pgJsonOut').textContent = JSON.stringify(sample, null, 2);
  }

  // Mobile nav
  const navToggle = document.getElementById('navToggle');
  const siteNav = document.getElementById('siteNav');
  if (navToggle && siteNav) {
    navToggle.addEventListener('click', () => {
      const open = siteNav.classList.toggle('is-open');
      navToggle.setAttribute('aria-expanded', String(open));
    });
    siteNav.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', () => {
        siteNav.classList.remove('is-open');
        navToggle.setAttribute('aria-expanded', 'false');
      });
    });
  }

  // Bind events
  document.querySelectorAll('.genre-btn').forEach((btn) => {
    btn.addEventListener('click', () => selectGenre(btn.dataset.genre));
  });

  document.querySelectorAll('.sheet-tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      activeTabKey = tab.dataset.sheetTab;
      document.querySelectorAll('.sheet-tab').forEach((t) => {
        const active = t.dataset.sheetTab === activeTabKey;
        t.classList.toggle('is-active', active);
        t.setAttribute('aria-selected', String(active));
      });
      renderDemo();
    });
  });

  document.getElementById('targetSlider').addEventListener('input', (e) => {
    currentTargetPrice = Number(e.target.value);
    renderDemo();
  });

  document.getElementById('simMonthly').addEventListener('input', updateSavings);
  document.getElementById('simKitPrice').addEventListener('change', updateSavings);

  ['pgMode', 'pgItem', 'pgTarget', 'pgDelay'].forEach((id) => {
    const el = document.getElementById(id);
    el.addEventListener(el.tagName === 'SELECT' ? 'change' : 'input', updateConfigPlayground);
  });

  // Init
  selectGenre('electronics');
  updateSavings();
  updateConfigPlayground();
})();
