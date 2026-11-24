/**
 * ツール4: ポケカBOX・カード 資産管理＆利回りポートフォリオ コントローラー
 * localStorage保存（完全クライアント完結・サーバー費0円）・CSV入出力・ツール1連携
 */
import {
  POPULAR_POKECA_BOXES,
  PORTFOLIO_CATEGORIES,
  calculatePortfolioSummary,
  portfolioToCsv,
  parsePortfolioCsv,
} from './calculators.js';
import {
  initCommonChrome,
  formatYen,
  formatPercent,
  escapeHtml,
  renderContextualRecommendation,
  buildXShareUrl,
  copyTextWithToast,
} from './common.js';

initCommonChrome('portfolio');

const STORAGE_KEY = 'tcg_profit_lab_portfolio_v1';

const SAMPLE_ITEMS = [
  {
    id: 'sample_1',
    name: 'ポケモンカード151',
    category: 'box',
    condition: 'シュリンク有',
    quantity: 2,
    buyPrice: 5800,
    currentPrice: 18500,
    note: 'ポケセン当選品',
  },
  {
    id: 'sample_2',
    name: 'テラスタルフェスex',
    category: 'box',
    condition: 'シュリンク有',
    quantity: 3,
    buyPrice: 5500,
    currentPrice: 11200,
    note: '初回抽選',
  },
  {
    id: 'sample_3',
    name: 'ピカチュウex SAR',
    category: 'psa',
    condition: 'PSA10',
    quantity: 1,
    buyPrice: 36000,
    currentPrice: 52000,
    note: '自引き鑑定品',
  },
];

const el = {
  form: document.getElementById('portfolioForm'),
  editId: document.getElementById('pfEditId'),
  name: document.getElementById('pfName'),
  category: document.getElementById('pfCategory'),
  condition: document.getElementById('pfCondition'),
  quantity: document.getElementById('pfQuantity'),
  buyPrice: document.getElementById('pfBuyPrice'),
  currentPrice: document.getElementById('pfCurrentPrice'),
  note: document.getElementById('pfNote'),
  submitBtn: document.getElementById('pfSubmitBtn'),
  cancelEditBtn: document.getElementById('pfCancelEditBtn'),
  datalist: document.getElementById('popularBoxList'),

  sortSelect: document.getElementById('pfSortSelect'),
  loadSampleBtn: document.getElementById('pfLoadSampleBtn'),
  exportCsvBtn: document.getElementById('pfExportCsvBtn'),
  importCsvInput: document.getElementById('pfImportCsvInput'),
  clearAllBtn: document.getElementById('pfClearAllBtn'),

  totalMarketVal: document.getElementById('pfTotalMarket'),
  totalCostVal: document.getElementById('pfTotalCost'),
  totalPnlVal: document.getElementById('pfTotalPnl'),
  totalPnlMeta: document.getElementById('pfTotalPnlMeta'),
  fleaNetVal: document.getElementById('pfFleaNet'),
  fleaNetMeta: document.getElementById('pfFleaNetMeta'),

  categoryBar: document.getElementById('pfCategoryBar'),
  categoryLegend: document.getElementById('pfCategoryLegend'),
  tableContainer: document.getElementById('pfTableContainer'),
  recContainer: document.getElementById('pfRecBox'),
  shareBtn: document.getElementById('pfShareBtn'),
  copyBtn: document.getElementById('pfCopyBtn'),
  copyToast: document.getElementById('pfCopyToast'),
};

if (el.datalist) {
  el.datalist.innerHTML = POPULAR_POKECA_BOXES.map((b) => `<option value="${escapeHtml(b)}"></option>`).join('');
}

let items = loadItems();
let lastShareText = '';

function loadItems() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveItems() {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch {
    // localStorage quota or private mode fallback
  }
}

function resetForm() {
  el.editId.value = '';
  el.form.reset();
  el.quantity.value = '1';
  el.condition.value = 'シュリンク有';
  el.submitBtn.textContent = '保有リストに追加';
  el.cancelEditBtn.hidden = true;
}

function startEdit(id) {
  const target = items.find((i) => i.id === id);
  if (!target) return;
  el.editId.value = target.id;
  el.name.value = target.name;
  el.category.value = target.category;
  el.condition.value = target.condition;
  el.quantity.value = String(target.quantity);
  el.buyPrice.value = String(target.buyPrice);
  el.currentPrice.value = String(target.currentPrice);
  el.note.value = target.note || '';
  el.submitBtn.textContent = '変更を保存';
  el.cancelEditBtn.hidden = false;
  el.name.focus();
}

function render() {
  const summary = calculatePortfolioSummary(items);

  el.totalMarketVal.textContent = formatYen(summary.totalMarketValue);
  el.totalCostVal.textContent = `総取得原価 ${formatYen(summary.totalCost)}（計 ${summary.totalQuantity}点）`;

  el.totalPnlVal.textContent = formatYen(summary.totalPnl, { signed: true });
  el.totalPnlVal.className = `kpi-value num ${summary.totalPnl >= 0 ? 'is-positive' : 'is-negative'}`;
  el.totalPnlMeta.textContent = `利回り ${formatPercent(summary.totalRoi, { signed: true })}`;

  el.fleaNetVal.textContent = formatYen(summary.totalEstimatedFleaNet);
  el.fleaNetMeta.textContent = `メルカリ10%＋送料控除後の実質損益 ${formatYen(summary.netPnlAfterFlea, { signed: true })}`;

  // カテゴリ構成バー
  if (summary.categoryBreakdown.length > 0) {
    el.categoryBar.innerHTML = summary.categoryBreakdown
      .map((c) => `<div class="cat-seg-${c.key}" style="width:${c.share.toFixed(2)}%" title="${escapeHtml(c.label)} ${c.share.toFixed(1)}%"></div>`)
      .join('');
    el.categoryLegend.innerHTML = summary.categoryBreakdown
      .map(
        (c) => `<span><span class="legend-dot cat-seg-${c.key}"></span>${escapeHtml(c.label)} ${formatYen(c.marketValue)}（${c.share.toFixed(1)}%）</span>`
      )
      .join('');
  } else {
    el.categoryBar.innerHTML = '';
    el.categoryLegend.innerHTML = '<span>アイテムを追加するとカテゴリ構成比率が表示されます</span>';
  }

  // ソート
  const sorted = [...summary.items];
  const sortMode = el.sortSelect.value;
  if (sortMode === 'pnl_desc') {
    sorted.sort((a, b) => b.pnl - a.pnl);
  } else if (sortMode === 'value_desc') {
    sorted.sort((a, b) => b.marketValue - a.marketValue);
  } else if (sortMode === 'roi_desc') {
    sorted.sort((a, b) => b.roi - a.roi);
  }

  if (sorted.length === 0) {
    el.tableContainer.innerHTML = `
      <div class="empty-state">
        <p><strong>まだ保有アイテムが登録されていません</strong></p>
        <p>左のフォームから追加するか、「サンプルを読み込む」で試せます。データはお使いのブラウザ内だけに安全に保存されます。</p>
      </div>
    `;
  } else {
    el.tableContainer.innerHTML = `
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>商品名 / 状態</th>
              <th class="num-cell">数量</th>
              <th class="num-cell">取得単価</th>
              <th class="num-cell">現在相場</th>
              <th class="num-cell">含み損益 (ROI)</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            ${sorted
              .map((item) => {
                const catLabel = PORTFOLIO_CATEGORIES[item.category]?.label || 'BOX';
                const sellType = item.category === 'psa' ? 'psa' : item.category === 'single' ? 'single' : 'box';
                const compareUrl = `./sell-compare.html?type=${sellType}&flea=${item.currentPrice}&cost=${item.buyPrice}&name=${encodeURIComponent(item.name)}`;
                const pnlCls = item.pnl >= 0 ? 'is-positive' : 'is-negative';
                return `
                  <tr>
                    <td>
                      <strong>${escapeHtml(item.name)}</strong><br>
                      <span class="badge badge-muted">${escapeHtml(catLabel)}</span>
                      <span class="kpi-meta">${escapeHtml(item.condition)}${item.note ? ` ／ ${escapeHtml(item.note)}` : ''}</span>
                    </td>
                    <td class="num-cell">${item.quantity}</td>
                    <td class="num-cell">${formatYen(item.buyPrice)}</td>
                    <td class="num-cell"><strong>${formatYen(item.currentPrice)}</strong></td>
                    <td class="num-cell">
                      <strong class="${pnlCls}">${formatYen(item.pnl, { signed: true })}</strong><br>
                      <span class="kpi-meta">${formatPercent(item.roi, { signed: true })}</span>
                    </td>
                    <td>
                      <div style="display:flex;gap:6px;flex-wrap:nowrap;">
                        <a class="btn btn-secondary btn-sm" href="${compareUrl}" title="この商品の売却手取りを比較">売却比較</a>
                        <button type="button" class="btn btn-ghost btn-sm" data-edit-item="${escapeHtml(item.id)}">編集</button>
                        <button type="button" class="btn btn-danger-outline btn-sm" data-delete-item="${escapeHtml(item.id)}">削除</button>
                      </div>
                    </td>
                  </tr>
                `;
              })
              .join('')}
          </tbody>
        </table>
      </div>
    `;

    el.tableContainer.querySelectorAll('[data-edit-item]').forEach((btn) => {
      btn.addEventListener('click', () => startEdit(btn.dataset.editItem));
    });
    el.tableContainer.querySelectorAll('[data-delete-item]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const id = btn.dataset.deleteItem;
        items = items.filter((i) => i.id !== id);
        saveItems();
        if (el.editId.value === id) resetForm();
        render();
      });
    });
  }

  renderContextualRecommendation(el.recContainer, {
    category: 'supplies',
    title: '長期保有BOX・カードの資産価値を守る保管ポイント',
    fallbackTip:
      '未開封BOXはシュリンク破れ・角潰れ・日焼けだけで買取査定が20〜40%下がることがあります。専用ローダーや防湿保管を徹底し、定期的なCSVバックアップもおすすめです。',
  });

  lastShareText = `ポケカ保有ポートフォリオ集計（計${summary.totalQuantity}点）：総評価額${formatYen(summary.totalMarketValue)}／含み損益${formatYen(summary.totalPnl, { signed: true })}（利回り${formatPercent(summary.totalRoi, { signed: true })}）！`;
  el.shareBtn.href = buildXShareUrl(lastShareText, 'portfolio.html');
}

el.form.addEventListener('submit', (e) => {
  e.preventDefault();
  const payload = {
    id: el.editId.value || `item_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
    name: el.name.value.trim(),
    category: el.category.value,
    condition: el.condition.value.trim() || 'シュリンク有',
    quantity: Math.max(1, Math.round(Number(el.quantity.value) || 1)),
    buyPrice: Math.max(0, Math.round(Number(el.buyPrice.value) || 0)),
    currentPrice: Math.max(0, Math.round(Number(el.currentPrice.value) || 0)),
    note: el.note.value.trim(),
  };

  if (!payload.name) return;

  if (el.editId.value) {
    items = items.map((i) => (i.id === payload.id ? payload : i));
  } else {
    items.unshift(payload);
  }

  saveItems();
  resetForm();
  render();
});

el.cancelEditBtn.addEventListener('click', resetForm);
el.sortSelect.addEventListener('change', render);

el.loadSampleBtn.addEventListener('click', () => {
  items = SAMPLE_ITEMS.map((s) => ({ ...s }));
  saveItems();
  resetForm();
  render();
});

el.exportCsvBtn.addEventListener('click', () => {
  const csv = `\uFEFF${portfolioToCsv(items)}`;
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `tcg-portfolio-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
});

el.importCsvInput.addEventListener('change', async (e) => {
  const file = e.target.files?.[0];
  if (!file) return;
  const text = await file.text();
  const imported = parsePortfolioCsv(text);
  if (imported.length > 0) {
    items = [...imported, ...items];
    saveItems();
    render();
    el.copyToast.textContent = `${imported.length}件をCSVから読み込みました`;
  } else {
    el.copyToast.textContent = '読み込めるデータが見つかりませんでした';
  }
  e.target.value = '';
});

el.clearAllBtn.addEventListener('click', () => {
  if (items.length === 0) return;
  if (!window.confirm('登録済みの保有リストをすべて削除しますか？（必要なら先にCSV出力してください）')) return;
  items = [];
  saveItems();
  resetForm();
  render();
});

el.copyBtn.addEventListener('click', () => copyTextWithToast(lastShareText, el.copyToast));

render();
