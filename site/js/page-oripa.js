/**
 * ツール3: オリパ 還元率・期待値・爆死確率シミュレーター コントローラー
 */
import {
  ORIPA_PRESETS,
  calculateOripaSimulation,
  simulateOripaDraws,
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

initCommonChrome('oripa');

const el = {
  presetButtons: document.querySelectorAll('[data-oripa-preset]'),
  unitPrice: document.getElementById('oripaUnitPrice'),
  totalPacks: document.getElementById('oripaTotalPacks'),
  drawCount: document.getElementById('oripaDrawCount'),
  missValue: document.getElementById('oripaMissValue'),
  cashoutRate: document.getElementById('oripaCashoutRate'),
  cashoutRateLabel: document.getElementById('oripaCashoutRateLabel'),
  prizeList: document.getElementById('oripaPrizeList'),
  addPrizeBtn: document.getElementById('addPrizeBtn'),
  missCountNote: document.getElementById('oripaMissCountNote'),

  verdictBox: document.getElementById('oripaVerdictBox'),
  verdictKicker: document.getElementById('oripaVerdictKicker'),
  verdictHeadline: document.getElementById('oripaVerdictHeadline'),
  verdictSub: document.getElementById('oripaVerdictSub'),

  returnRateVal: document.getElementById('oripaReturnRate'),
  cashoutReturnVal: document.getElementById('oripaCashoutReturn'),
  probAdVal: document.getElementById('oripaProbAd'),
  probAllMissVal: document.getElementById('oripaProbAllMiss'),
  probTopVal: document.getElementById('oripaProbTop'),
  evPerPackMeta: document.getElementById('oripaEvMeta'),

  drawTableBody: document.getElementById('oripaDrawTableBody'),
  gachaBtn1: document.getElementById('gachaDraw1Btn'),
  gachaBtn5: document.getElementById('gachaDraw5Btn'),
  gachaBtn10: document.getElementById('gachaDraw10Btn'),
  gachaSummary: document.getElementById('gachaSummary'),
  gachaResults: document.getElementById('gachaResults'),

  recContainer: document.getElementById('oripaRecBox'),
  shareBtn: document.getElementById('oripaShareBtn'),
  copyBtn: document.getElementById('oripaCopyBtn'),
  copyToast: document.getElementById('oripaCopyToast'),
};

let prizes = [];
let currentSim = null;
let lastShareText = '';

function renderPrizeInputs() {
  el.prizeList.innerHTML = prizes
    .map(
      (p, idx) => `
      <div class="prize-row" data-prize-idx="${idx}">
        <input type="text" class="input-control" data-field="name" value="${escapeHtml(p.name)}" placeholder="賞名（例: S賞）" aria-label="賞名 ${idx + 1}">
        <div class="input-wrap">
          <input type="number" class="input-control has-suffix" data-field="value" value="${p.value}" min="0" step="100" aria-label="評価額 ${idx + 1}">
          <span class="input-suffix">円</span>
        </div>
        <div class="input-wrap">
          <input type="number" class="input-control has-suffix" data-field="count" value="${p.count}" min="0" step="1" aria-label="本数 ${idx + 1}">
          <span class="input-suffix">口</span>
        </div>
        <button type="button" class="btn btn-danger-outline" data-remove-prize="${idx}" aria-label="この当たり枠を削除">削除</button>
      </div>
    `
    )
    .join('');

  el.prizeList.querySelectorAll('input').forEach((input) => {
    input.addEventListener('input', (e) => {
      const row = e.target.closest('[data-prize-idx]');
      const idx = Number(row.dataset.prizeIdx);
      const field = e.target.dataset.field;
      if (field === 'name') {
        prizes[idx].name = e.target.value;
      } else {
        prizes[idx][field] = Math.max(0, Number(e.target.value) || 0);
      }
      update();
    });
  });

  el.prizeList.querySelectorAll('[data-remove-prize]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const idx = Number(btn.dataset.removePrize);
      prizes.splice(idx, 1);
      renderPrizeInputs();
      update();
    });
  });
}

function loadPreset(key) {
  const preset = ORIPA_PRESETS[key];
  if (!preset) return;
  el.presetButtons.forEach((b) => b.classList.toggle('is-active', b.dataset.oripaPreset === key));
  el.unitPrice.value = String(preset.unitPrice);
  el.totalPacks.value = String(preset.totalPacks);
  el.drawCount.value = String(preset.drawCount);
  el.missValue.value = String(preset.missValue);
  el.cashoutRate.value = String(Math.round(preset.cashoutRate * 100));
  prizes = preset.prizes.map((p) => ({ ...p }));
  renderPrizeInputs();
  el.gachaResults.innerHTML = '';
  el.gachaSummary.textContent = 'ボタンを押すと設定した確率（非復元）で実際に運試しできます。';
  update();
}

function update() {
  const cashoutPct = Math.max(10, Math.min(100, Number(el.cashoutRate.value) || 80));
  el.cashoutRateLabel.textContent = `${cashoutPct}%（相場比）`;

  const sim = calculateOripaSimulation({
    unitPrice: el.unitPrice.value,
    totalPacks: el.totalPacks.value,
    drawCount: el.drawCount.value,
    missValue: el.missValue.value,
    cashoutRate: cashoutPct / 100,
    prizes,
  });
  currentSim = sim;

  if (!sim.isValid) {
    el.missCountNote.textContent = sim.error;
    el.missCountNote.style.color = 'var(--danger)';
    el.verdictBox.className = 'verdict-box is-negative';
    el.verdictKicker.textContent = '入力エラー';
    el.verdictHeadline.textContent = '当たり本数が総口数を超えています';
    el.verdictSub.textContent = sim.error;
    return;
  }

  el.missCountNote.textContent = `ハズレ枠の自動計算：残り ${sim.missCount.toLocaleString('ja-JP')} 口（全体の ${((sim.missCount / sim.totalPacks) * 100).toFixed(1)}%）`;
  el.missCountNote.style.color = 'var(--ink-secondary)';

  el.verdictBox.className = 'verdict-box';
  if (sim.grade === 'S' || sim.grade === 'A') {
    el.verdictBox.classList.add('is-positive');
  } else if (sim.grade === 'B') {
    el.verdictBox.classList.add('is-gold');
  } else {
    el.verdictBox.classList.add('is-negative');
  }

  el.verdictKicker.textContent = `総合判定ランク ${sim.grade}：${sim.gradeLabel}`;
  el.verdictHeadline.textContent = `販売相場ベース還元率 ${formatPercent(sim.returnRate)}（現金化目安 ${formatPercent(sim.cashoutReturnRate)}）`;
  el.verdictSub.textContent = `${sim.drawCount}口購入（${formatYen(sim.totalSpend)}）時の1回以上アド確率は ${formatPercent(sim.probAtLeastOneAd)}、全外れ（爆死）確率は ${formatPercent(sim.probAllMiss)} です。`;

  el.returnRateVal.textContent = formatPercent(sim.returnRate);
  el.returnRateVal.className = `kpi-value num ${sim.returnRate >= 90 ? 'is-positive' : sim.returnRate < 70 ? 'is-negative' : 'is-gold'}`;
  el.evPerPackMeta.textContent = `1口あたり期待値 ${formatYen(sim.evPerPack)}（現金化 ${formatYen(sim.cashoutEvPerPack)}）`;

  el.cashoutReturnVal.textContent = formatPercent(sim.cashoutReturnRate);
  el.probAdVal.textContent = formatPercent(sim.probAtLeastOneAd);
  el.probAllMissVal.textContent = formatPercent(sim.probAllMiss);
  el.probAllMissVal.className = `kpi-value num ${sim.probAllMiss >= 50 ? 'is-negative' : 'is-positive'}`;
  el.probTopVal.textContent = formatPercent(sim.probTopPrize, { digits: 2 });

  // 口数シミュレーション表
  el.drawTableBody.innerHTML = sim.drawTable
    .map(
      (row) => `
      <tr class="${row.isCurrent ? 'is-current' : ''}">
        <td><strong>${row.draws}口</strong> ${row.isCurrent ? '<span class="badge badge-gold">選択中</span>' : ''}</td>
        <td class="num-cell">${formatYen(row.totalSpend)}</td>
        <td class="num-cell">${formatYen(row.expectedReturn)}</td>
        <td class="num-cell"><strong class="${row.probAtLeastOneAd >= 50 ? 'is-positive' : ''}">${formatPercent(row.probAtLeastOneAd)}</strong></td>
        <td class="num-cell"><strong class="${row.probAllMiss >= 50 ? 'is-negative' : ''}">${formatPercent(row.probAllMiss)}</strong></td>
        <td class="num-cell">${formatPercent(row.probTopPrize, { digits: 2 })}</td>
      </tr>
    `
    )
    .join('');

  renderContextualRecommendation(el.recContainer, {
    category: 'oripa',
    title: 'オリパで大きく負けないためのチェックポイント',
    fallbackTip:
      '表記の販売相場ベースで還元率95%に見えても、実際に売却（現金化）すると75〜80%程度になるのが一般的です。総口数・最低保証・残り口数が明記されているオリパを選び、予算上限を決めて楽しむのが鉄則です。',
  });

  lastShareText = `オリパ期待値計算（1口${formatYen(sim.unitPrice)}×総${sim.totalPacks}口）：還元率${formatPercent(sim.returnRate)}（現金化目安${formatPercent(sim.cashoutReturnRate)}）。${sim.drawCount}口引いた時のアド確率${formatPercent(sim.probAtLeastOneAd)}／爆死率${formatPercent(sim.probAllMiss)}！`;
  el.shareBtn.href = buildXShareUrl(lastShareText, 'oripa.html');
}

function runGacha(count) {
  if (!currentSim || !currentSim.isValid) return;
  const draws = simulateOripaDraws(currentSim, count);
  const spend = draws.length * currentSim.unitPrice;
  const totalValue = draws.reduce((acc, d) => acc + d.value, 0);
  const diff = totalValue - spend;

  el.gachaSummary.innerHTML = `<strong>${draws.length}連結果：</strong>投資 ${formatYen(spend)} → 獲得評価額 ${formatYen(totalValue)}（収支 <strong class="${diff >= 0 ? 'is-positive' : 'is-negative'}">${formatYen(diff, { signed: true })}</strong>）`;

  el.gachaResults.innerHTML = draws
    .map((d) => {
      const cls = d.isTop ? 'is-top' : d.isAd ? 'is-ad' : '';
      const tag = d.isTop
        ? '<span class="badge badge-gold">大当たり</span>'
        : d.isAd
          ? '<span class="badge badge-brand">アド</span>'
          : '<span class="badge badge-muted">ハズレ</span>';
      return `
        <div class="gacha-chip ${cls}">
          <span>#${d.drawNumber} ${escapeHtml(d.name)} ${tag}</span>
          <span class="num">${formatYen(d.value)}（${formatYen(d.net, { signed: true })}）</span>
        </div>
      `;
    })
    .join('');
}

el.presetButtons.forEach((btn) => {
  btn.addEventListener('click', () => loadPreset(btn.dataset.oripaPreset));
});

el.addPrizeBtn.addEventListener('click', () => {
  prizes.push({ name: `C賞（枠${prizes.length + 1}）`, value: 1500, count: 5 });
  renderPrizeInputs();
  update();
});

[el.unitPrice, el.totalPacks, el.drawCount, el.missValue, el.cashoutRate].forEach((inp) =>
  inp.addEventListener('input', update)
);

el.gachaBtn1.addEventListener('click', () => runGacha(1));
el.gachaBtn5.addEventListener('click', () => runGacha(5));
el.gachaBtn10.addEventListener('click', () => runGacha(10));
el.copyBtn.addEventListener('click', () => copyTextWithToast(lastShareText, el.copyToast));

loadPreset('mild');
