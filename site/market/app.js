/**
 * ポケカ未開封BOX 買取相場インデックス（匿名統計UI）
 * Zero specific store names — aggregates market high/median/low, MSRP ratio,
 * no-shrink gap, 30-day SVG sparklines, and portfolio calculator mode.
 */

const DATA_URL = './data/market_index.json';
const HOLDINGS_STORAGE_KEY = 'pokeca_market_holdings_v1';
const SERIES_ORDER = ['MEGA', 'SV', 'スペシャルBOX', 'S&S', 'SM', 'XY・BW', '旧裏・その他'];

const state = {
  payload: null,
  items: [],
  query: '',
  series: 'ALL',
  sort: 'default',
  multiOnly: true,
  noShrinkOnly: false,
  heldOnly: false,
  portfolioMode: false,
  holdings: loadHoldings(),
  modalItemId: null,
};

const els = {};

function $(id) {
  return document.getElementById(id);
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function fmtYen(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—';
  return `¥${Math.round(Number(value)).toLocaleString('ja-JP')}`;
}

function fmtSignedYen(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—';
  const n = Math.round(Number(value));
  if (n > 0) return `+¥${n.toLocaleString('ja-JP')}`;
  if (n < 0) return `-¥${Math.abs(n).toLocaleString('ja-JP')}`;
  return '±0';
}

function fmtPct(rate, digits = 1) {
  if (rate === null || rate === undefined || Number.isNaN(Number(rate))) return '—';
  return `${(Number(rate) * 100).toFixed(digits)}%`;
}

function deltaClass(value) {
  if (value === null || value === undefined) return 'is-flat';
  const n = Number(value);
  if (n > 0) return 'is-up';
  if (n < 0) return 'is-down';
  return 'is-flat';
}

function seriesBadgeClass(series) {
  switch (series) {
    case 'MEGA':
      return 'series-badge--MEGA';
    case 'SV':
      return 'series-badge--SV';
    case 'スペシャルBOX':
      return 'series-badge--SP';
    case 'S&S':
      return 'series-badge--SS';
    case 'SM':
      return 'series-badge--SM';
    default:
      return 'series-badge--OLD';
  }
}

function loadHoldings() {
  try {
    const raw = window.localStorage.getItem(HOLDINGS_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return {};
    const clean = {};
    for (const [key, qty] of Object.entries(parsed)) {
      const n = Math.max(0, Math.min(999, Math.floor(Number(qty) || 0)));
      if (n > 0) clean[key] = n;
    }
    return clean;
  } catch {
    return {};
  }
}

function saveHoldings() {
  try {
    window.localStorage.setItem(HOLDINGS_STORAGE_KEY, JSON.stringify(state.holdings));
  } catch {
    // Ignore storage quota / private-mode restrictions.
  }
}

function setHoldingQty(itemId, nextQty) {
  const clamped = Math.max(0, Math.min(999, Math.floor(Number(nextQty) || 0)));
  if (clamped <= 0) {
    delete state.holdings[itemId];
  } else {
    state.holdings[itemId] = clamped;
  }
  saveHoldings();
  renderList();
  renderPortfolioDock();
}

function sellCompareUrl(item) {
  const params = new URLSearchParams();
  params.set('type', 'box');
  params.set('name', item.name);
  params.set('buyback', String(item.high_yen));
  if (item.mercari_break_even_yen) {
    params.set('flea', String(item.mercari_break_even_yen));
  }
  if (item.msrp_yen) {
    params.set('cost', String(item.msrp_yen));
  }
  return `../sell-compare.html?${params.toString()}`;
}

function renderSparklineSvg(points, { width = 92, height = 28 } = {}) {
  if (!Array.isArray(points) || points.length < 2) {
    return '<span class="is-flat" style="font-size:0.72rem;">集計開始</span>';
  }
  const prices = points.map((p) => Number(p.price));
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const padX = 3;
  const padY = 4;
  const innerW = width - padX * 2;
  const innerH = height - padY * 2;
  const span = max - min;

  const coords = prices.map((price, idx) => {
    const x = padX + (innerW * idx) / (prices.length - 1);
    const y = span === 0 ? padY + innerH / 2 : padY + innerH * (1 - (price - min) / span);
    return [Number(x.toFixed(1)), Number(y.toFixed(1))];
  });

  const first = prices[0];
  const last = prices[prices.length - 1];
  const stroke = last > first ? '#0c6b53' : last < first ? '#b83227' : '#6c7480';
  const poly = coords.map(([x, y]) => `${x},${y}`).join(' ');
  const [lastX, lastY] = coords[coords.length - 1];
  const titleText = `${points[0].date} ${fmtYen(first)} → ${points[points.length - 1].date} ${fmtYen(last)}`;

  return `
    <svg class="sparkline-svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(titleText)}">
      <title>${escapeHtml(titleText)}</title>
      <polyline fill="none" stroke="${stroke}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" points="${poly}"></polyline>
      <circle cx="${lastX}" cy="${lastY}" r="2.6" fill="${stroke}"></circle>
    </svg>
  `;
}

function renderDetailChartSvg(points) {
  if (!Array.isArray(points) || points.length < 2) {
    return '<div class="empty-state" style="padding:18px;">推移グラフは2日以上の日次データ蓄積後に表示されます。</div>';
  }
  const width = 600;
  const height = 175;
  const padLeft = 64;
  const padRight = 18;
  const padTop = 14;
  const padBottom = 26;
  const innerW = width - padLeft - padRight;
  const innerH = height - padTop - padBottom;

  const prices = points.map((p) => Number(p.price));
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const margin = Math.max(500, Math.round((max - min) * 0.12));
  const yMin = Math.max(0, min - margin);
  const yMax = max + margin;
  const ySpan = Math.max(1, yMax - yMin);

  const coords = points.map((pt, idx) => {
    const x = padLeft + (innerW * idx) / (points.length - 1);
    const y = padTop + innerH * (1 - (Number(pt.price) - yMin) / ySpan);
    return { x: Number(x.toFixed(1)), y: Number(y.toFixed(1)), date: pt.date, price: Number(pt.price) };
  });

  const first = prices[0];
  const last = prices[prices.length - 1];
  const stroke = last >= first ? '#0c6b53' : '#b83227';
  const fill = last >= first ? 'rgba(12, 107, 83, 0.10)' : 'rgba(184, 50, 39, 0.10)';

  const linePath = coords.map((c, i) => `${i === 0 ? 'M' : 'L'}${c.x},${c.y}`).join(' ');
  const areaPath = `${linePath} L${coords[coords.length - 1].x},${padTop + innerH} L${coords[0].x},${padTop + innerH} Z`;

  const yTicks = [yMax, Math.round((yMax + yMin) / 2), yMin];
  const gridLines = yTicks
    .map((val) => {
      const y = (padTop + innerH * (1 - (val - yMin) / ySpan)).toFixed(1);
      return `
        <line x1="${padLeft}" y1="${y}" x2="${width - padRight}" y2="${y}" stroke="#e2ddd2" stroke-dasharray="3 3"></line>
        <text x="${padLeft - 8}" y="${Number(y) + 4}" text-anchor="end" font-size="11" fill="#6c7480">${escapeHtml(fmtYen(val))}</text>
      `;
    })
    .join('');

  const xLabels = [
    coords[0],
    coords[Math.floor(coords.length / 2)],
    coords[coords.length - 1],
  ]
    .map(
      (c) =>
        `<text x="${c.x}" y="${height - 6}" text-anchor="middle" font-size="11" fill="#6c7480">${escapeHtml(c.date.slice(5))}</text>`
    )
    .join('');

  const dots = coords
    .map(
      (c) =>
        `<circle cx="${c.x}" cy="${c.y}" r="3" fill="${stroke}"><title>${escapeHtml(c.date)}: ${escapeHtml(fmtYen(c.price))}</title></circle>`
    )
    .join('');

  return `
    <svg viewBox="0 0 ${width} ${height}" style="width:100%;height:auto;display:block;" role="img" aria-label="30日価格推移チャート">
      ${gridLines}
      <path d="${areaPath}" fill="${fill}"></path>
      <path d="${linePath}" fill="none" stroke="${stroke}" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"></path>
      ${dots}
      ${xLabels}
    </svg>
  `;
}

function renderSummary() {
  const payload = state.payload;
  const s = payload.summary || {};

  const storeCount = payload.monitored_store_count || 0;
  els.storeCountBadge.textContent = storeCount > 0 ? `主要${storeCount}店舗 匿名集計` : '複数店舗 匿名集計';
  const updatedLabel = payload.fetched_at
    ? payload.fetched_at.replace('T', ' ').slice(0, 16)
    : payload.as_of_date || '—';
  els.updatedAtBadge.textContent = `更新: ${updatedLabel} JST`;

  const mood = s.mood_label || '横ばい';
  els.kpiMoodBadge.textContent = mood;
  els.kpiMoodBadge.className = 'mood-badge';
  if (mood.includes('弱気') || mood.includes('下落')) {
    els.kpiMoodBadge.classList.add('mood-badge--down');
  } else if (!mood.includes('強気') && !mood.includes('上昇')) {
    els.kpiMoodBadge.classList.add('mood-badge--flat');
  }

  els.kpiPrevBreadth.innerHTML = `<span class="is-up">↑${s.prev_up_count ?? 0}</span> / <span class="is-down">↓${s.prev_down_count ?? 0}</span>`;
  els.kpiWeekBreadth.textContent = `7日前比: ↑${s.week_up_count ?? 0} / ↓${s.week_down_count ?? 0}`;

  els.kpiTotalBoxes.textContent = `${s.total_boxes ?? state.items.length} BOX`;
  els.kpiMultiBoxes.textContent = `2店以上比較: ${s.multi_store_boxes ?? 0}（3店以上: ${s.three_plus_store_boxes ?? 0}）`;

  els.kpiMedianSpread.textContent = fmtPct(s.median_spread_rate ?? 0, 1);
  els.kpiHighSpread.textContent = `差率5%以上の注目BOX: ${s.high_spread_box_count ?? 0}件`;

  els.kpiNoShrinkCount.textContent = `${s.no_shrink_compared_boxes ?? 0} BOX`;
  els.kpiHistoryDays.textContent = `日次アーカイブ: ${s.history_days ?? 0}日分`;

  // Movers
  const gainers = payload.highlights?.week_gainers || [];
  const losers = payload.highlights?.week_losers || [];
  if (gainers.length || losers.length) {
    els.moversSection.hidden = false;
    els.weekGainersList.innerHTML = gainers.length
      ? gainers
          .map(
            (m) => `
          <button type="button" class="mover-chip" data-mover-query="${escapeHtml(m.product_name)}">
            <span>${escapeHtml(m.product_name)}</span>
            <span class="mover-chip__delta is-up num">${escapeHtml(fmtSignedYen(m.diff_yen))}</span>
          </button>`
          )
          .join('')
      : '<span class="is-flat" style="font-size:0.78rem;">該当なし</span>';

    els.weekLosersList.innerHTML = losers.length
      ? losers
          .map(
            (m) => `
          <button type="button" class="mover-chip" data-mover-query="${escapeHtml(m.product_name)}">
            <span>${escapeHtml(m.product_name)}</span>
            <span class="mover-chip__delta is-down num">${escapeHtml(fmtSignedYen(m.diff_yen))}</span>
          </button>`
          )
          .join('')
      : '<span class="is-flat" style="font-size:0.78rem;">該当なし</span>';
  }
}

function renderSeriesPills() {
  const counts = {};
  for (const item of state.items) {
    if (state.multiOnly && item.store_count < 2) continue;
    if (state.noShrinkOnly && item.no_shrink_high_yen === null) continue;
    counts[item.series] = (counts[item.series] || 0) + 1;
  }
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  const availableSeries = SERIES_ORDER.filter((s) => (counts[s] || 0) > 0);

  const pillsHtml = [
    `<button type="button" class="series-pill ${state.series === 'ALL' ? 'is-active' : ''}" data-series="ALL">すべて <span class="series-pill__count num">${total}</span></button>`,
    ...availableSeries.map(
      (series) => `
      <button type="button" class="series-pill ${state.series === series ? 'is-active' : ''}" data-series="${escapeHtml(series)}">
        ${escapeHtml(series)} <span class="series-pill__count num">${counts[series]}</span>
      </button>`
    ),
    `<span class="result-meta num" id="resultCount"></span>`,
  ].join('');

  els.seriesPills.innerHTML = pillsHtml;
  els.resultCount = $('resultCount');
}

function getFilteredItems() {
  const q = state.query.trim().toLowerCase();
  const list = state.items.filter((item) => {
    if (state.multiOnly && item.store_count < 2) return false;
    if (state.noShrinkOnly && item.no_shrink_high_yen === null) return false;
    if (state.heldOnly && !(state.holdings[item.id] > 0)) return false;
    if (state.series !== 'ALL' && item.series !== state.series) return false;
    if (q) {
      const hay = `${item.name} ${item.id} ${item.set_code || ''} ${item.series}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });

  const sorted = [...list];
  switch (state.sort) {
    case 'high_desc':
      sorted.sort((a, b) => b.high_yen - a.high_yen);
      break;
    case 'ratio_desc':
      sorted.sort((a, b) => (b.msrp_ratio ?? -1) - (a.msrp_ratio ?? -1) || b.high_yen - a.high_yen);
      break;
    case 'spread_desc':
      sorted.sort((a, b) => b.spread_rate - a.spread_rate || b.spread_yen - a.spread_yen);
      break;
    case 'week_desc':
      sorted.sort((a, b) => (b.week_diff_yen ?? -9e9) - (a.week_diff_yen ?? -9e9));
      break;
    case 'week_asc':
      sorted.sort((a, b) => (a.week_diff_yen ?? 9e9) - (b.week_diff_yen ?? 9e9));
      break;
    case 'noshrink_gap_desc':
      sorted.sort((a, b) => (b.no_shrink_gap_yen ?? -1) - (a.no_shrink_gap_yen ?? -1));
      break;
    default:
      break;
  }
  return sorted;
}

function renderRatioBadge(ratio) {
  if (ratio === null || ratio === undefined) return '<span class="is-flat">—</span>';
  const cls = ratio >= 3.0 ? 'ratio-pill--hot' : ratio >= 1.5 ? 'ratio-pill--solid' : '';
  return `<span class="ratio-pill num ${cls}">${Number(ratio).toFixed(1)}倍</span>`;
}

function renderSpreadCell(item) {
  if (item.store_count < 2) {
    return '<span class="is-flat" style="font-size:0.74rem;">単独掲載</span>';
  }
  const rateCls = item.spread_rate >= 0.05 ? 'spread-hot' : '';
  const yenCls = item.spread_yen >= 3000 ? 'spread-gold' : '';
  return `
    <div class="delta-stack">
      <span class="num ${rateCls}">${fmtPct(item.spread_rate, 1)}</span>
      <span class="delta-sub num ${yenCls}">${fmtYen(item.spread_yen)}</span>
    </div>
  `;
}

function renderNoShrinkCell(item) {
  if (item.no_shrink_high_yen === null || item.no_shrink_high_yen === undefined) {
    return '<span class="is-flat">—</span>';
  }
  const gapSub =
    item.no_shrink_gap_yen !== null
      ? `-${fmtYen(item.no_shrink_gap_yen)} (${fmtPct(item.no_shrink_gap_rate, 0)})`
      : '';
  return `
    <div class="delta-stack">
      <span class="num" style="font-weight:700;">${fmtYen(item.no_shrink_high_yen)}</span>
      <span class="delta-sub num">${escapeHtml(gapSub)}</span>
    </div>
  `;
}

function renderActionCell(item) {
  if (state.portfolioMode) {
    const qty = state.holdings[item.id] || 0;
    return `
      <div class="qty-stepper" data-stepper-id="${escapeHtml(item.id)}">
        <button type="button" class="qty-btn" data-qty-delta="-1" aria-label="1箱減らす">−</button>
        <input type="number" class="qty-input num" min="0" max="999" value="${qty}" data-qty-input aria-label="${escapeHtml(item.name)}の保有箱数">
        <button type="button" class="qty-btn" data-qty-delta="1" aria-label="1箱増やす">+</button>
      </div>
    `;
  }
  return `<a class="btn btn--sm" href="${escapeHtml(sellCompareUrl(item))}">フリマ比較</a>`;
}

function renderList() {
  const items = getFilteredItems();
  if (els.resultCount) {
    els.resultCount.textContent = `${items.length} / ${state.items.length} BOX 表示中`;
  }
  els.actionColHeader.textContent = state.portfolioMode ? '保有箱数' : '売却比較';

  if (!items.length) {
    const emptyMsg = '条件に一致するBOXがありません。検索語やフィルター条件を調整してください。';
    els.marketTableBody.innerHTML = `<tr><td colspan="9" class="empty-state">${emptyMsg}</td></tr>`;
    els.mobileCards.innerHTML = `<div class="table-card empty-state">${emptyMsg}</div>`;
    return;
  }

  els.marketTableBody.innerHTML = items
    .map((item) => {
      const heldQty = state.holdings[item.id] || 0;
      const rangeText =
        item.store_count >= 2
          ? `中央 ${fmtYen(item.median_yen)} / 下限 ${fmtYen(item.low_yen)}・${item.store_count}店`
          : '1店舗掲載';
      const subParts = [];
      if (item.set_code) subParts.push(escapeHtml(item.set_code));
      if (item.msrp_yen) subParts.push(`定価 ${fmtYen(item.msrp_yen)}`);
      if (item.condition_inferred) subParts.push('<span class="tag-warn">状態推定</span>');

      return `
        <tr class="${heldQty > 0 ? 'is-held' : ''}">
          <td><span class="series-badge ${seriesBadgeClass(item.series)}">${escapeHtml(item.series)}</span></td>
          <td>
            <button type="button" class="box-name-btn" data-detail-id="${escapeHtml(item.id)}">${escapeHtml(item.name)}</button>
            <div class="box-sub num">${subParts.join(' · ')}</div>
          </td>
          <td class="num">
            <div class="price-main">${fmtYen(item.high_yen)}</div>
            <div class="price-range-sub">${escapeHtml(rangeText)}</div>
          </td>
          <td class="center">${renderRatioBadge(item.msrp_ratio)}</td>
          <td class="num">
            <div class="delta-stack">
              <span class="delta-primary ${deltaClass(item.prev_diff_yen)}">${fmtSignedYen(item.prev_diff_yen)}</span>
              <span class="delta-sub ${deltaClass(item.week_diff_yen)}">7日 ${fmtSignedYen(item.week_diff_yen)}</span>
            </div>
          </td>
          <td class="num">${renderSpreadCell(item)}</td>
          <td class="num">${renderNoShrinkCell(item)}</td>
          <td class="num">${renderSparklineSvg(item.trend)}</td>
          <td class="center">${renderActionCell(item)}</td>
        </tr>
      `;
    })
    .join('');

  els.mobileCards.innerHTML = items
    .map((item) => {
      const heldQty = state.holdings[item.id] || 0;
      const rangeText =
        item.store_count >= 2
          ? `中央 ${fmtYen(item.median_yen)} / 下限 ${fmtYen(item.low_yen)}（${item.store_count}店）`
          : '1店舗掲載';
      return `
        <article class="box-card ${heldQty > 0 ? 'is-held' : ''}">
          <div class="box-card__head">
            <div>
              <span class="series-badge ${seriesBadgeClass(item.series)}">${escapeHtml(item.series)}</span>
              ${item.set_code ? `<span class="box-sub num" style="display:inline;margin-left:6px;">${escapeHtml(item.set_code)}</span>` : ''}
              <div style="margin-top:4px;">
                <button type="button" class="box-name-btn" data-detail-id="${escapeHtml(item.id)}">${escapeHtml(item.name)}</button>
              </div>
              <div class="price-range-sub num">${escapeHtml(rangeText)}</div>
            </div>
            <div style="text-align:right;flex-shrink:0;">
              <div class="price-main num">${fmtYen(item.high_yen)}</div>
              <div style="margin-top:3px;">${renderRatioBadge(item.msrp_ratio)}</div>
            </div>
          </div>
          <div class="box-card__metrics">
            <div>
              <div class="metric-cell__label">前回比 / 7日比</div>
              <div class="metric-cell__val num ${deltaClass(item.prev_diff_yen)}">${fmtSignedYen(item.prev_diff_yen)}</div>
              <div class="delta-sub num ${deltaClass(item.week_diff_yen)}">7日 ${fmtSignedYen(item.week_diff_yen)}</div>
            </div>
            <div>
              <div class="metric-cell__label">店間差</div>
              <div class="metric-cell__val num ${item.spread_rate >= 0.05 ? 'spread-hot' : ''}">${item.store_count >= 2 ? fmtPct(item.spread_rate, 1) : '—'}</div>
              <div class="delta-sub num">${item.store_count >= 2 ? fmtYen(item.spread_yen) : '単独'}</div>
            </div>
            <div>
              <div class="metric-cell__label">シュリンク無</div>
              <div class="metric-cell__val num">${item.no_shrink_high_yen !== null ? fmtYen(item.no_shrink_high_yen) : '—'}</div>
              <div class="delta-sub num">${item.no_shrink_gap_yen !== null ? `-${fmtYen(item.no_shrink_gap_yen)}` : ''}</div>
            </div>
          </div>
          <div class="box-card__foot">
            <div>${renderSparklineSvg(item.trend, { width: 108, height: 28 })}</div>
            <div style="display:flex;gap:6px;align-items:center;">
              <button type="button" class="btn btn--sm btn--ghost" data-detail-id="${escapeHtml(item.id)}">詳細</button>
              ${renderActionCell(item)}
            </div>
          </div>
        </article>
      `;
    })
    .join('');
}

function renderPortfolioDock() {
  let totalQty = 0;
  let highTotal = 0;
  let medianTotal = 0;
  let msrpKnownCost = 0;
  let msrpKnownHigh = 0;

  for (const item of state.items) {
    const qty = state.holdings[item.id] || 0;
    if (qty <= 0) continue;
    totalQty += qty;
    highTotal += item.high_yen * qty;
    medianTotal += (item.median_yen ?? item.high_yen) * qty;
    if (item.msrp_yen) {
      msrpKnownCost += item.msrp_yen * qty;
      msrpKnownHigh += item.high_yen * qty;
    }
  }

  const shouldShow = state.portfolioMode || totalQty > 0;
  els.portfolioDock.hidden = !shouldShow;
  els.heldOnlyWrap.hidden = totalQty === 0;
  if (totalQty === 0 && state.heldOnly) {
    state.heldOnly = false;
    els.heldOnlyCheck.checked = false;
  }

  els.dockQty.textContent = `${totalQty} BOX`;
  els.dockHighTotal.textContent = fmtYen(highTotal);
  els.dockMedianTotal.textContent = fmtYen(medianTotal);
  if (msrpKnownCost > 0) {
    const profit = msrpKnownHigh - msrpKnownCost;
    els.dockMsrpProfit.textContent = `${fmtSignedYen(profit)} (定価計 ${fmtYen(msrpKnownCost)})`;
  } else {
    els.dockMsrpProfit.textContent = '—';
  }
}

function exportHoldingsCsv() {
  const rows = [['シリーズ', 'BOX名', '型番', '保有箱数', '参考高値(単価)', '中央値(単価)', '定価(単価)', '評価額合計(高値)', '定価比含み益']];
  for (const item of state.items) {
    const qty = state.holdings[item.id] || 0;
    if (qty <= 0) continue;
    const totalHigh = item.high_yen * qty;
    const profit = item.msrp_yen ? (item.high_yen - item.msrp_yen) * qty : '';
    rows.push([
      item.series,
      item.name,
      item.set_code || '',
      qty,
      item.high_yen,
      item.median_yen ?? item.high_yen,
      item.msrp_yen ?? '',
      totalHigh,
      profit,
    ]);
  }
  if (rows.length <= 1) return;
  const csv = '\uFEFF' + rows.map((r) => r.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `pokeca-box-portfolio-${state.payload?.as_of_date || 'latest'}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function openDetailModal(itemId) {
  const item = state.items.find((i) => i.id === itemId);
  if (!item) return;
  state.modalItemId = itemId;

  els.detailSeries.textContent = item.series;
  els.detailSeries.className = `series-badge ${seriesBadgeClass(item.series)}`;
  els.detailTitle.textContent = item.name;

  const metaParts = [];
  if (item.set_code) metaParts.push(`型番: ${item.set_code}`);
  if (item.release_date) metaParts.push(`発売日: ${item.release_date}`);
  if (item.msrp_yen) metaParts.push(`公式定価: ${fmtYen(item.msrp_yen)}`);
  metaParts.push(`集計店舗数: ${item.store_count}店舗（匿名）`);
  els.detailMeta.textContent = metaParts.join(' ／ ');

  const stats = [
    { label: '参考高値（シュリンク有）', val: fmtYen(item.high_yen) },
    { label: '中央値 / 下限値', val: item.store_count >= 2 ? `${fmtYen(item.median_yen)} / ${fmtYen(item.low_yen)}` : '単独掲載' },
    { label: '定価倍率', val: item.msrp_ratio ? `${item.msrp_ratio.toFixed(2)}倍 (${fmtSignedYen(item.msrp_diff_yen)})` : '—' },
    { label: '前回比 / 7日前比', val: `${fmtSignedYen(item.prev_diff_yen)} / ${fmtSignedYen(item.week_diff_yen)}` },
    { label: '店間差（売却先選び幅）', val: item.store_count >= 2 ? `${fmtYen(item.spread_yen)} (${fmtPct(item.spread_rate, 1)})` : '—' },
    {
      label: 'シュリンク無 参考高値',
      val:
        item.no_shrink_high_yen !== null
          ? `${fmtYen(item.no_shrink_high_yen)} (-${fmtYen(item.no_shrink_gap_yen)})`
          : 'データなし',
    },
  ];
  els.detailStats.innerHTML = stats
    .map(
      (st) => `
      <div class="detail-stat">
        <div class="detail-stat__label">${escapeHtml(st.label)}</div>
        <div class="detail-stat__val num">${escapeHtml(st.val)}</div>
      </div>`
    )
    .join('');

  const pts = item.trend || [];
  if (pts.length >= 2) {
    const prices = pts.map((p) => p.price);
    els.detailChartRange.textContent = `期間安値 ${fmtYen(Math.min(...prices))} 〜 期間高値 ${fmtYen(Math.max(...prices))}（${pts.length}日分）`;
  } else {
    els.detailChartRange.textContent = `${pts.length}日分`;
  }
  els.detailChartContainer.innerHTML = renderDetailChartSvg(pts);

  els.detailBreakEven.innerHTML = `
    <strong>フリマ vs 買取店 損益分岐ライン（参考高値 ${fmtYen(item.high_yen)} 基準）</strong><br>
    ・<strong>メルカリ（手数料10%・コンパクト送料+梱包640円）:</strong> <span class="num" style="font-weight:700;">${fmtYen(item.mercari_break_even_yen)}</span> 以上で売れるならメルカリ有利<br>
    ・<strong>Yahoo!フリマ（手数料5%・送料+梱包640円）:</strong> <span class="num" style="font-weight:700;">${fmtYen(item.yahoo_break_even_yen)}</span> 以上で売れるならYahoo!フリマ有利
  `;

  els.detailSellCompareLink.href = sellCompareUrl(item);
  els.detailModal.hidden = false;
  document.body.style.overflow = 'hidden';
}

function closeDetailModal() {
  state.modalItemId = null;
  els.detailModal.hidden = true;
  document.body.style.overflow = '';
}

function bindEvents() {
  els.searchInput.addEventListener('input', () => {
    state.query = els.searchInput.value;
    els.searchClearBtn.hidden = !state.query;
    renderList();
  });

  els.searchClearBtn.addEventListener('click', () => {
    state.query = '';
    els.searchInput.value = '';
    els.searchClearBtn.hidden = true;
    renderList();
    els.searchInput.focus();
  });

  els.sortSelect.addEventListener('change', () => {
    state.sort = els.sortSelect.value;
    renderList();
  });

  els.multiOnlyCheck.addEventListener('change', () => {
    state.multiOnly = els.multiOnlyCheck.checked;
    renderSeriesPills();
    renderList();
  });

  els.noShrinkOnlyCheck.addEventListener('change', () => {
    state.noShrinkOnly = els.noShrinkOnlyCheck.checked;
    renderSeriesPills();
    renderList();
  });

  els.heldOnlyCheck.addEventListener('change', () => {
    state.heldOnly = els.heldOnlyCheck.checked;
    renderList();
  });

  els.togglePortfolioBtn.addEventListener('click', () => {
    state.portfolioMode = !state.portfolioMode;
    els.togglePortfolioBtn.setAttribute('aria-pressed', String(state.portfolioMode));
    els.togglePortfolioBtn.classList.toggle('btn--active', state.portfolioMode);
    els.togglePortfolioBtn.textContent = state.portfolioMode ? '資産計算モード中 ✓' : '保有BOX資産計算';
    renderList();
    renderPortfolioDock();
  });

  els.seriesPills.addEventListener('click', (event) => {
    const btn = event.target.closest('[data-series]');
    if (!btn) return;
    state.series = btn.dataset.series;
    renderSeriesPills();
    renderList();
  });

  els.moversSection.addEventListener('click', (event) => {
    const chip = event.target.closest('[data-mover-query]');
    if (!chip) return;
    const q = chip.dataset.moverQuery;
    state.query = q;
    state.series = 'ALL';
    state.multiOnly = false;
    els.searchInput.value = q;
    els.searchClearBtn.hidden = false;
    els.multiOnlyCheck.checked = false;
    renderSeriesPills();
    renderList();
  });

  function handleListClick(event) {
    const detailBtn = event.target.closest('[data-detail-id]');
    if (detailBtn) {
      openDetailModal(detailBtn.dataset.detailId);
      return;
    }
    const deltaBtn = event.target.closest('[data-qty-delta]');
    if (deltaBtn) {
      const wrap = deltaBtn.closest('[data-stepper-id]');
      if (!wrap) return;
      const id = wrap.dataset.stepperId;
      const current = state.holdings[id] || 0;
      setHoldingQty(id, current + Number(deltaBtn.dataset.qtyDelta));
    }
  }

  function handleListInput(event) {
    const input = event.target.closest('[data-qty-input]');
    if (!input) return;
    const wrap = input.closest('[data-stepper-id]');
    if (!wrap) return;
    setHoldingQty(wrap.dataset.stepperId, input.value);
  }

  els.marketTableBody.addEventListener('click', handleListClick);
  els.marketTableBody.addEventListener('change', handleListInput);
  els.mobileCards.addEventListener('click', handleListClick);
  els.mobileCards.addEventListener('change', handleListInput);

  els.dockCsvBtn.addEventListener('click', exportHoldingsCsv);
  els.dockClearBtn.addEventListener('click', () => {
    state.holdings = {};
    state.heldOnly = false;
    els.heldOnlyCheck.checked = false;
    saveHoldings();
    renderList();
    renderPortfolioDock();
  });

  els.detailCloseBtn.addEventListener('click', closeDetailModal);
  els.detailCloseBtn2.addEventListener('click', closeDetailModal);
  els.detailModal.addEventListener('click', (event) => {
    if (event.target === els.detailModal) closeDetailModal();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !els.detailModal.hidden) {
      closeDetailModal();
    }
  });
}

async function init() {
  for (const id of [
    'storeCountBadge',
    'updatedAtBadge',
    'kpiMoodBadge',
    'kpiPrevBreadth',
    'kpiWeekBreadth',
    'kpiTotalBoxes',
    'kpiMultiBoxes',
    'kpiMedianSpread',
    'kpiHighSpread',
    'kpiNoShrinkCount',
    'kpiHistoryDays',
    'moversSection',
    'weekGainersList',
    'weekLosersList',
    'searchInput',
    'searchClearBtn',
    'sortSelect',
    'multiOnlyCheck',
    'noShrinkOnlyCheck',
    'heldOnlyWrap',
    'heldOnlyCheck',
    'togglePortfolioBtn',
    'seriesPills',
    'actionColHeader',
    'marketTableBody',
    'mobileCards',
    'portfolioDock',
    'dockQty',
    'dockHighTotal',
    'dockMedianTotal',
    'dockMsrpProfit',
    'dockCsvBtn',
    'dockClearBtn',
    'detailModal',
    'detailSeries',
    'detailTitle',
    'detailMeta',
    'detailStats',
    'detailChartRange',
    'detailChartContainer',
    'detailBreakEven',
    'detailSellCompareLink',
    'detailCloseBtn',
    'detailCloseBtn2',
  ]) {
    els[id] = $(id);
  }

  bindEvents();

  try {
    const res = await fetch(DATA_URL, { cache: 'no-cache' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const payload = await res.json();
    state.payload = payload;
    state.items = Array.isArray(payload.items) ? payload.items : [];
    renderSummary();
    renderSeriesPills();
    renderList();
    renderPortfolioDock();
  } catch (err) {
    const msg = `相場データの読み込みに失敗しました (${err.message})。ページを再読み込みしてください。`;
    els.marketTableBody.innerHTML = `<tr><td colspan="9" class="empty-state">${escapeHtml(msg)}</td></tr>`;
    els.mobileCards.innerHTML = `<div class="table-card empty-state">${escapeHtml(msg)}</div>`;
  }
}

init();
