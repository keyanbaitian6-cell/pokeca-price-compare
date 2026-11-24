/**
 * ツール2: PSA鑑定 損益分岐点＆期待値シミュレーター コントローラー
 */
import { PSA_PLAN_PRESETS, calculatePsaSimulation } from './calculators.js';
import {
  initCommonChrome,
  formatYen,
  formatPercent,
  escapeHtml,
  renderContextualRecommendation,
  buildXShareUrl,
  copyTextWithToast,
} from './common.js';

initCommonChrome('psa');

const el = {
  planSelect: document.getElementById('psaPlanSelect'),
  rawCardCost: document.getElementById('rawCardCost'),
  gradingFee: document.getElementById('gradingFee'),
  cardCount: document.getElementById('cardCount'),
  totalShippingCost: document.getElementById('totalShippingCost'),
  sellFeeRate: document.getElementById('psaSellFeeRate'),
  sellShipping: document.getElementById('psaSellShipping'),
  pricePsa10: document.getElementById('pricePsa10'),
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
};

el.planSelect.innerHTML = PSA_PLAN_PRESETS.map(
  (p) => `<option value="${p.id}">${escapeHtml(p.label)}</option>`
).join('');
el.planSelect.value = 'jp_bulk';

let lastShareText = '';

function update() {
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

  el.probPsa10Label.textContent = `${res.probPsa10}%`;
  el.probBreakdownLabel.textContent = `想定内訳：PSA10 ${res.probPsa10}% ／ PSA9 ${res.probPsa9}% ／ PSA8以下 ${res.probPsa8OrLower}%`;

  // 判定バナー
  el.verdictBox.className = 'verdict-box';
  if (res.verdict === 'submit') {
    el.verdictBox.classList.add('is-positive');
    el.verdictKicker.textContent = '鑑定提出の期待値：プラス';
    el.verdictHeadline.textContent = `1枚あたり期待利益 ${formatYen(res.expectedProfitPerCard, { signed: true })}（ROI ${formatPercent(res.expectedRoi, { signed: true })}）`;
    el.verdictSub.textContent = `${res.cardCount}枚提出時の期待合計利益は ${formatYen(res.expectedTotalProfit, { signed: true })}。素体のまま売却するより期待値が ${formatYen(res.advantageOverRawSale, { signed: true })} 高い計算です。`;
  } else if (res.verdict === 'caution') {
    el.verdictBox.classList.add('is-gold');
    el.verdictKicker.textContent = '期待値は微プラス（素体売却と比較推奨）';
    el.verdictHeadline.textContent = `1枚あたり期待利益 ${formatYen(res.expectedProfitPerCard, { signed: true })}`;
    el.verdictSub.textContent = '鑑定期間中の相場下落リスクや返送待ち時間（1〜3ヶ月）を考えると、状態が完璧な個体だけ厳選提出するのが無難です。';
  } else {
    el.verdictBox.classList.add('is-negative');
    el.verdictKicker.textContent = '鑑定提出の期待値：マイナス';
    el.verdictHeadline.textContent = `1枚あたり期待損益 ${formatYen(res.expectedProfitPerCard, { signed: true })}`;
    el.verdictSub.textContent =
      res.requiredPsa10Rate === null
        ? 'PSA10を取っても鑑定料・手数料で赤字になる水準です。素体売却またはまとめ買いでの原価圧縮を検討してください。'
        : `黒字化するにはPSA10取得率が ${formatPercent(res.requiredPsa10Rate)} 以上必要です。センタリング・白欠けを厳しく検品しましょう。`;
  }

  // サマリーKPI
  el.totalCostPerCard.textContent = formatYen(res.totalCostPerCard);
  el.totalCostMeta.textContent = `素体 ${formatYen(res.rawCardCost)} ＋ 鑑定 ${formatYen(res.gradingFeePerCard)} ＋ 送料按分 ${formatYen(res.shippingPerCard)}`;

  el.breakEven10.textContent = `${formatYen(res.breakEvenPsa10Price)}〜`;
  el.requiredRate.textContent =
    res.requiredPsa10Rate === null
      ? '黒字不可'
      : res.requiredPsa10Rate === 0
        ? '0%（全パターン黒字）'
        : `${formatPercent(res.requiredPsa10Rate)}以上`;

  el.expectedTotalProfit.textContent = formatYen(res.expectedTotalProfit, { signed: true });
  el.expectedTotalProfit.className = `kpi-value num ${res.expectedTotalProfit >= 0 ? 'is-positive' : 'is-negative'}`;

  // グレード別カード
  const applyGrade = (valEl, metaEl, g) => {
    valEl.textContent = formatYen(g.profit, { signed: true });
    valEl.className = `kpi-value num ${g.profit > 0 ? 'is-positive' : g.profit < 0 ? 'is-negative' : ''}`;
    metaEl.textContent = `売却手取り ${formatYen(g.net)} ／ ROI ${formatPercent(g.roi, { signed: true })}`;
  };
  applyGrade(el.grade10Profit, el.grade10Meta, res.grades.psa10);
  applyGrade(el.grade9Profit, el.grade9Meta, res.grades.psa9);
  applyGrade(el.grade8Profit, el.grade8Meta, res.grades.psa8);

  // 勝率別テーブル
  el.sensitivityBody.innerHTML = res.sensitivityTable
    .map((row) => {
      const isCurrent = Math.abs(row.psa10Rate - res.probPsa10) < 5;
      const cls = row.expectedProfitPerCard >= 0 ? 'is-positive' : 'is-negative';
      return `
        <tr class="${isCurrent ? 'is-current' : ''}">
          <td><strong>PSA10率 ${row.psa10Rate}%</strong> ${isCurrent ? '<span class="badge badge-gold">現在の想定</span>' : ''}</td>
          <td class="num-cell"><strong class="${cls}">${formatYen(row.expectedProfitPerCard, { signed: true })}</strong></td>
          <td class="num-cell">${formatYen(row.expectedTotalProfit, { signed: true })}</td>
          <td class="num-cell">${formatPercent(row.roi, { signed: true })}</td>
        </tr>
      `;
    })
    .join('');

  // 文脈連動おすすめ枠
  renderContextualRecommendation(el.recContainer, {
    category: res.verdict === 'skip' ? 'buyback' : 'psa',
    title: res.verdict === 'skip' ? '鑑定より素体売却が向いている場合' : 'PSA提出コストと不備リスクを抑える準備',
    fallbackTip:
      res.verdict === 'skip'
        ? 'PSA10とPSA9の価格差が小さいカードや鑑定料比率が高い中価格帯カードは、素体のままフリマまたは高額買取店へ売却する方が資金効率が高くなります。'
        : '1〜2枚だけ送ると往復送料の按分が重くなります。5〜10枚まとめてバリューバルク提出し、カードセーバー1＋新品スリーブで丁寧に検品するのが勝率アップの王道です。',
  });

  const reqLabel = res.requiredPsa10Rate === null ? '黒字不可' : `${res.requiredPsa10Rate.toFixed(1)}%`;
  lastShareText = `PSA鑑定シミュレーション：素体${formatYen(res.rawCardCost)}→PSA10想定${formatYen(res.grades.psa10.price)}（取得率${res.probPsa10}%）で期待利益${formatYen(res.expectedProfitPerCard, { signed: true })}/枚！損益分岐のPSA10最低取得率は${reqLabel}。`;
  el.shareBtn.href = buildXShareUrl(lastShareText, 'psa.html');
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
