/**
 * ツール2 V2: PSA鑑定 損益分岐点＆期待値シミュレーター（2026年11月 公式料金対応）
 */
import { PSA_PLAN_PRESETS, calculatePsaSimulation } from './calculators.js';
import {
  initCommonChrome,
  bindStickyMobileBar,
  formatYen,
  formatPercent,
  escapeHtml,
  renderContextualRecommendation,
  buildXShareUrl,
  copyTextWithToast,
  saveJsonState,
  loadJsonState,
} from './common.js';

initCommonChrome('psa');

const STORAGE_KEY = 'tcg_profit_lab_psa_v2';

const el = {
  planSelect: document.getElementById('psaPlanSelect'),
  rawCardCost: document.getElementById('rawCardCost'),
  pricePsa10: document.getElementById('pricePsa10'),
  settingsSummary: document.getElementById('psaSettingsSummary'),
  planEtaNote: document.getElementById('psaPlanEtaNote'),
  gradingFee: document.getElementById('gradingFee'),
  cardCount: document.getElementById('cardCount'),
  totalShippingCost: document.getElementById('totalShippingCost'),
  sellFeeRate: document.getElementById('psaSellFeeRate'),
  sellShipping: document.getElementById('psaSellShipping'),
  pricePsa9: document.getElementById('pricePsa9'),
  pricePsa8: document.getElementById('pricePsa8'),
  probPsa10: document.getElementById('probPsa10'),
  probPsa10Label: document.getElementById('probPsa10Label'),
  probBreakdownLabel: document.getElementById('probBreakdownLabel'),

  verdictBox: document.getElementById('psaVerdictBox'),
  verdictKicker: document.getElementById('psaVerdictKicker'),
  verdictHeadline: document.getElementById('psaVerdictHeadline'),
  verdictSub: document.getElementById('psaVerdictSub'),

  totalCostPerCard: document.getElementById('psaTotalCost'),
  totalCostMeta: document.getElementById('psaTotalCostMeta'),
  breakEven10: document.getElementById('psaBreakEven10'),
  requiredRate: document.getElementById('psaRequiredRate'),
  expectedTotalProfit: document.getElementById('psaExpectedTotalProfit'),

  grade10Profit: document.getElementById('grade10Profit'),
  grade10Meta: document.getElementById('grade10Meta'),
  grade9Profit: document.getElementById('grade9Profit'),
  grade9Meta: document.getElementById('grade9Meta'),
  grade8Profit: document.getElementById('grade8Profit'),
  grade8Meta: document.getElementById('grade8Meta'),

  sensitivityBody: document.getElementById('psaSensitivityBody'),
  recContainer: document.getElementById('psaRecBox'),
  shareBtn: document.getElementById('psaShareBtn'),
  copyBtn: document.getElementById('psaCopyBtn'),
  copyToast: document.getElementById('psaCopyToast'),

  stickyBar: document.getElementById('psaStickyBar'),
  stickyTitle: document.getElementById('psaStickyTitle'),
  stickySub: document.getElementById('psaStickySub'),
};

el.planSelect.innerHTML = PSA_PLAN_PRESETS.map(
  (p) => `<option value="${p.id}">${escapeHtml(p.label)}</option>`
).join('');

const saved = loadJsonState(STORAGE_KEY);
if (saved && typeof saved === 'object') {
  el.planSelect.value = PSA_PLAN_PRESETS.some((p) => p.id === saved.planId) ? saved.planId : 'jp_value';
  el.rawCardCost.value = String(saved.rawCardCost ?? 12000);
  el.pricePsa10.value = String(saved.pricePsa10 ?? 34000);
  el.gradingFee.value = String(saved.gradingFee ?? 5980);
  el.cardCount.value = String(saved.cardCount ?? 5);
  el.totalShippingCost.value = String(saved.totalShippingCost ?? 2500);
  el.sellFeeRate.value = String(saved.sellFeeRate ?? 10);
  el.sellShipping.value = String(saved.sellShipping ?? 210);
  el.pricePsa9.value = String(saved.pricePsa9 ?? 13000);
  el.pricePsa8.value = String(saved.pricePsa8 ?? 8000);
  el.probPsa10.value = String(saved.probPsa10 ?? 70);
} else {
  el.planSelect.value = 'jp_value';
}

let lastShareText = '';

function update() {
  const plan = PSA_PLAN_PRESETS.find((p) => p.id === el.planSelect.value);
  if (el.planEtaNote) {
    el.planEtaNote.textContent = plan && plan.eta !== '—' ? `予定納期目安：${plan.eta}` : '';
  }

  const res = calculatePsaSimulation({
    rawCardCost: el.rawCardCost.value,
    gradingFeePerCard: el.gradingFee.value,
    cardCount: el.cardCount.value,
    totalShippingCost: el.totalShippingCost.value,
    sellFeeRate: (Number(el.sellFeeRate.value) || 0) / 100,
    sellShippingPerCard: el.sellShipping.value,
    pricePsa10: el.pricePsa10.value,
    pricePsa9: el.pricePsa9.value,
    pricePsa8OrLower: el.pricePsa8.value,
    probPsa10: el.probPsa10.value,
  });

  if (el.settingsSummary) {
    el.settingsSummary.textContent = `${res.cardCount}枚提出・送料按分${formatYen(res.shippingPerCard)}・PSA10率${res.probPsa10}%・売却手数料${el.sellFeeRate.value}%`;
  }

  el.probPsa10Label.textContent = `${res.probPsa10}%`;
  el.probBreakdownLabel.textContent = `内訳想定：PSA10 ${res.probPsa10}% ／ PSA9 ${res.probPsa9}% ／ PSA8以下 ${res.probPsa8OrLower}%`;

  el.verdictBox.className = 'verdict-card';
  if (res.verdict === 'submit') {
    el.verdictBox.classList.add('is-positive');
    el.verdictKicker.textContent = '鑑定提出の期待値：プラス';
    el.verdictHeadline.textContent = `1枚あたり期待利益 ${formatYen(res.expectedProfitPerCard, { signed: true })}（ROI ${formatPercent(res.expectedRoi, { signed: true })}）`;
    el.verdictSub.textContent = `${res.cardCount}枚提出時の期待合計利益 ${formatYen(res.expectedTotalProfit, { signed: true })}。素体売却より ${formatYen(res.advantageOverRawSale, { signed: true })} 有利です。`;
  } else if (res.verdict === 'caution') {
    el.verdictBox.classList.add('is-gold');
    el.verdictKicker.textContent = '期待値は微プラス（厳選提出推奨）';
    el.verdictHeadline.textContent = `1枚あたり期待利益 ${formatYen(res.expectedProfitPerCard, { signed: true })}`;
    el.verdictSub.textContent = '返送までの数ヶ月間の相場変動リスクを考慮し、状態完璧な個体のみ提出するのが安全です。';
  } else {
    el.verdictBox.classList.add('is-negative');
    el.verdictKicker.textContent = '鑑定提出の期待値：マイナス';
    el.verdictHeadline.textContent = `1枚あたり期待損益 ${formatYen(res.expectedProfitPerCard, { signed: true })}`;
    el.verdictSub.textContent =
      res.requiredPsa10Rate === null
        ? 'PSA10を取っても鑑定料・手数料で赤字になる水準です。素体売却をおすすめします。'
        : `黒字化するにはPSA10率が ${formatPercent(res.requiredPsa10Rate)} 以上必要です。`;
  }

  if (el.stickyTitle) {
    el.stickyTitle.textContent = `PSA期待値 ${formatYen(res.expectedProfitPerCard, { signed: true })}/枚`;
  }
  if (el.stickySub) {
    const reqText = res.requiredPsa10Rate === null ? '黒字不可' : `必要PSA10率 ${formatPercent(res.requiredPsa10Rate)}`;
    el.stickySub.textContent = `PSA10損益分岐 ${formatYen(res.breakEvenPsa10Price)}〜 ／ ${reqText}`;
  }

  el.totalCostPerCard.textContent = formatYen(res.totalCostPerCard);
  el.totalCostMeta.textContent = `素体${formatYen(res.rawCardCost)}＋鑑定${formatYen(res.gradingFeePerCard)}＋送料${formatYen(res.shippingPerCard)}`;

  el.breakEven10.textContent = `${formatYen(res.breakEvenPsa10Price)}〜`;
  el.requiredRate.textContent =
    res.requiredPsa10Rate === null
      ? '黒字不可'
      : res.requiredPsa10Rate === 0
        ? '0%（全黒字）'
        : `${formatPercent(res.requiredPsa10Rate)}以上`;

  el.expectedTotalProfit.textContent = formatYen(res.expectedTotalProfit, { signed: true });
  el.expectedTotalProfit.className = `kpi-value num ${res.expectedTotalProfit >= 0 ? 'is-positive' : 'is-negative'}`;

  const applyGrade = (valEl, metaEl, g) => {
    valEl.textContent = formatYen(g.profit, { signed: true });
    valEl.className = `kpi-value num ${g.profit > 0 ? 'is-positive' : g.profit < 0 ? 'is-negative' : ''}`;
    metaEl.textContent = `手取り ${formatYen(g.net)} ／ ROI ${formatPercent(g.roi, { signed: true })}`;
  };
  applyGrade(el.grade10Profit, el.grade10Meta, res.grades.psa10);
  applyGrade(el.grade9Profit, el.grade9Meta, res.grades.psa9);
  applyGrade(el.grade8Profit, el.grade8Meta, res.grades.psa8);

  el.sensitivityBody.innerHTML = res.sensitivityTable
    .map((row) => {
      const isCurrent = Math.abs(row.psa10Rate - res.probPsa10) < 5;
      const cls = row.expectedProfitPerCard >= 0 ? 'is-positive' : 'is-negative';
      return `
        <tr class="${isCurrent ? 'is-current' : ''}">
          <td><strong>PSA10率 ${row.psa10Rate}%</strong> ${isCurrent ? '<span class="badge badge-gold">現在</span>' : ''}</td>
          <td class="num-cell"><strong class="${cls}">${formatYen(row.expectedProfitPerCard, { signed: true })}</strong></td>
          <td class="num-cell">${formatYen(row.expectedTotalProfit, { signed: true })}</td>
          <td class="num-cell">${formatPercent(row.roi, { signed: true })}</td>
        </tr>
      `;
    })
    .join('');

  renderContextualRecommendation(el.recContainer, {
    category: res.verdict === 'skip' ? 'buyback' : 'psa',
    title: res.verdict === 'skip' ? '鑑定より素体売却が向いている場合' : 'PSA提出コストと不備リスクを抑える準備',
    fallbackTip:
      res.verdict === 'skip'
        ? '鑑定料（バリュー5,980円）の比率が高い中価格帯カードは、素体のままフリマや高額買取へ回す方が資金効率が高くなります。'
        : 'PSA公式ルールでは「縦入れ両面透明スリーブ＋カードセーバー1」での提出が必須です。複数枚まとめ出しで返送料・保険料の1枚あたり負担を抑えましょう。',
  });

  const reqLabel = res.requiredPsa10Rate === null ? '黒字不可' : `${res.requiredPsa10Rate.toFixed(1)}%`;
  lastShareText = `PSA鑑定シミュレーション：素体${formatYen(res.rawCardCost)}→PSA10想定${formatYen(res.grades.psa10.price)}（取得率${res.probPsa10}%）で期待利益${formatYen(res.expectedProfitPerCard, { signed: true })}/枚！黒字に必要なPSA10率は${reqLabel}。`;
  el.shareBtn.href = buildXShareUrl(lastShareText, 'psa.html');

  saveJsonState(STORAGE_KEY, {
    planId: el.planSelect.value,
    rawCardCost: Number(el.rawCardCost.value) || 0,
    pricePsa10: Number(el.pricePsa10.value) || 0,
    gradingFee: Number(el.gradingFee.value) || 0,
    cardCount: Number(el.cardCount.value) || 1,
    totalShippingCost: Number(el.totalShippingCost.value) || 0,
    sellFeeRate: Number(el.sellFeeRate.value) || 0,
    sellShipping: Number(el.sellShipping.value) || 0,
    pricePsa9: Number(el.pricePsa9.value) || 0,
    pricePsa8: Number(el.pricePsa8.value) || 0,
    probPsa10: Number(el.probPsa10.value) || 70,
  });
}

el.planSelect.addEventListener('change', () => {
  const plan = PSA_PLAN_PRESETS.find((p) => p.id === el.planSelect.value);
  if (plan && plan.fee !== null) {
    el.gradingFee.value = String(plan.fee);
  }
  update();
});

el.gradingFee.addEventListener('input', () => {
  el.planSelect.value = 'custom';
  update();
});

[
  el.rawCardCost,
  el.cardCount,
  el.totalShippingCost,
  el.sellFeeRate,
  el.sellShipping,
  el.pricePsa10,
  el.pricePsa9,
  el.pricePsa8,
  el.probPsa10,
].forEach((input) => input.addEventListener('input', update));

el.copyBtn.addEventListener('click', () => copyTextWithToast(lastShareText, el.copyToast));

update();

bindStickyMobileBar({
  targetEl: el.verdictBox,
  barEl: el.stickyBar,
  scrollToSelector: '#psaVerdictBox',
});
