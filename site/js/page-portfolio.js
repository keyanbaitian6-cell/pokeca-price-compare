/**
 * ツール4 V2: ポケカBOX・カード 資産ポートフォリオ コントローラー
 * - サマリー＋保有リストをファーストビューに配置
 * - 追加/編集フォームは「＋ アイテムを追加」ボタンで開閉（視認性最優先）
 * - スマホでも横スクロール不要のレスポンシブカード表示
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
  toggleFormBtn: document.getElementById('pfToggleFormBtn'),
  formPanel: document.getElementById('pfFormPanel'),
  formTitle: document.getElementById('pfFormTitle'),
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
  listContainer: document.getElementById('pfTableContainer'),
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
    // ignore storage errors
  }
}

function openForm(isEdit = false) {
  if (el.formPanel) el.formPanel.hidden = false;
  if (el.formTitle) el.formTitle.textContent = isEdit ? 'アイテムを編集' : '新しいアイテムを追加';
  if (el.toggleFormBtn) el.toggleFormBtn.textContent = '入力フォームを閉じる';
}

function closeForm() {
  if (el.formPanel) el.formPanel.hidden = true;
  if (el.toggleFormBtn) el.toggleFormBtn.textContent = '＋ アイテムを追加';
}

function resetForm(hide = false) {
  el.editId.value = '';
  el.form.reset();
  el.quantity.value = '1';
  el.condition.value = 'シュリンク有';
  el.submitBtn.textContent = '保有リストに追加';
  el.cancelEditBtn.hidden = true;
  if (hide) closeForm();
}

function startEdit(id) {
  const target = items.find((i) => i.id === id);
  if (!target) return;
  openForm(true);
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
  el.formPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  el.name.focus();
}

function render() {
  const summary = calculatePortfolioSummary(items);

  el.totalMarketVal.textContent = formatYen(summary.totalMarketValue);
  el.totalCostVal.textContent = `取得原価 ${formatYen(summary.totalCost)}（計 ${summary.totalQuantity}点）`;

  el.totalPnlVal.textContent = formatYen(summary.totalPnl, { signed: true });
  el.totalPnlVal.className = `kpi-value num ${summary.totalPnl >= 0 ? 'is-positive' : 'is-negative'}`;
  el.totalPnlMeta.textContent = `利回り ${formatPercent(summary.totalRoi, { signed: true })}`;

  el.fleaNetVal.textContent = formatYen(summary.totalEstimatedFleaNet);
  el.fleaNetMeta.textContent = `メルカリ控除後の実質損益 ${formatYen(summary.netPnlAfterFlea, { signed: true })}`;

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
    el.listContainer.innerHTML = `
      <div class="empty-state">
        <p><strong>まだ保有アイテムがありません</strong></p>
        <p>上の「＋ アイテムを追加」または「サンプル読込」で今すぐ試せます。データはお使いのブラウザ内だけに保存されます。</p>
      </div>
    `;
  } else {
    el.listContainer.innerHTML = `
      <div class="portfolio-cards">
        ${sorted
          .map((item) => {
            const catLabel = PORTFOLIO_CATEGORIES[item.category]?.label || 'BOX';
            const sellType = item.category === 'psa' ? 'psa' : item.category === 'single' ? 'single' : 'box';
            const compareUrl = `./sell-compare.html?type=${sellType}&flea=${item.currentPrice}&cost=${item.buyPrice}&name=${encodeURIComponent(item.name)}`;
            const pnlCls = item.pnl >= 0 ? 'is-positive' : 'is-negative';
            return `
              <div class="pf-item-card">
                <div>
                  <div class="pf-item-name">${escapeHtml(item.name)}</div>
                  <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                    <span class="badge badge-muted">${escapeHtml(catLabel)}</span>
                    <span class="kpi-meta">${escapeHtml(item.condition)} × ${item.quantity}点${item.note ? ` ／ ${escapeHtml(item.note)}` : ''}</span>
                  </div>
                  <div class="kpi-meta" style="margin-top:4px;">取得 ${formatYen(item.buyPrice)} → 現在 ${formatYen(item.currentPrice)}（評価額 ${formatYen(item.marketValue)}）</div>
                </div>
                <div class="pf-item-nums">
                  <div class="pf-item-pnl ${pnlCls}">${formatYen(item.pnl, { signed: true })}</div>
                  <div class="kpi-meta">ROI ${formatPercent(item.roi, { signed: true })}</div>
                </div>
                <div class="pf-item-actions">
                  <a class="btn btn-primary btn-sm" href="${compareUrl}">売却比較</a>
                  <button type="button" class="btn btn-secondary btn-sm" data-edit-item="${escapeHtml(item.id)}">編集</button>
                  <button type="button" class="btn btn-danger-outline btn-sm" data-delete-item="${escapeHtml(item.id)}">削除</button>
                </div>
              </div>
            `;
          })
          .join('')}
      </div>
    `;

    el.listContainer.querySelectorAll('[data-edit-item]').forEach((btn) => {
      btn.addEventListener('click', () => startEdit(btn.dataset.editItem));
    });
    el.listContainer.querySelectorAll('[data-delete-item]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const id = btn.dataset.deleteItem;
        items = items.filter((i) => i.id !== id);
        saveItems();
        if (el.editId.value === id) resetForm(true);
        render();
      });
    });
  }

  renderContextualRecommendation(el.recContainer, {
    category: 'supplies',
    title: '長期保有BOX・カードの資産価値を守る保管ポイント',
    fallbackTip:
      '未開封BOXはシュリンク破れ・角潰れ・日焼けだけで買取査定が20〜40%下がることがあります。専用UVローダーや防湿保管を徹底し、定期的なCSVバックアップもおすすめです。',
  });

  lastShareText = `ポケカ保有ポートフォリオ（計${summary.totalQuantity}点）：総評価額${formatYen(summary.totalMarketValue)}／含み損益${formatYen(summary.totalPnl, { signed: true })}（利回り${formatPercent(summary.totalRoi, { signed: true })}）！`;
  el.shareBtn.href = buildXShareUrl(lastShareText, 'portfolio.html');
}

if (el.toggleFormBtn) {
  el.toggleFormBtn.addEventListener('click', () => {
    if (el.formPanel.hidden) {
      resetForm(false);
      openForm(false);
      el.name.focus();
    } else {
      resetForm(true);
    }
  });
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
  resetForm(true);
  render();
});

el.cancelEditBtn.addEventListener('click', () => resetForm(true));
el.sortSelect.addEventListener('change', render);

el.loadSampleBtn.addEventListener('click', () => {
  items = SAMPLE_ITEMS.map((s) => ({ ...s }));
  saveItems();
  resetForm(true);
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
  if (!window.confirm('登録済みの保有リストをすべて削除しますか？')) return;
  items = [];
  saveItems();
  resetForm(true);
  render();
});

el.copyBtn.addEventListener('click', () => copyTextWithToast(lastShareText, el.copyToast));

render();
