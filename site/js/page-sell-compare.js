/**
 * ツール1: フリマ vs 買取店 手取り最大比較コントローラー
 * index.html / sell-compare.html の両方で動作（URLクエリからの価格引き継ぎにも対応）
 */
import {
  ITEM_TYPE_PRESETS,
  PLATFORM_PRESETS,
  SHIPPING_PRESETS,
  calculateSellComparison,
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

export function initSellComparePage(activePageId = 'sell-compare') {
  initCommonChrome(activePageId);

  const el = {
    presetButtons: document.querySelectorAll('[data-item-preset]'),
    itemName: document.getElementById('sellItemName'),
    fleaPrice: document.getElementById('fleaPrice'),
    platformSelect: document.getElementById('platformSelect'),
    feeRate: document.getElementById('feeRate'),
    shippingPreset: document.getElementById('shippingPreset'),
    shippingCost: document.getElementById('shippingCost'),
    packingCost: document.getElementById('packingCost'),
    buybackPrice: document.getElementById('buybackPrice'),
    buybackCost: document.getElementById('buybackCost'),
    purchaseCost: document.getElementById('purchaseCost'),
    effortCost: document.getElementById('effortCost'),
    effortCostLabel: document.getElementById('effortCostLabel'),

    verdictBox: document.getElementById('verdictBox'),
    verdictKicker: document.getElementById('verdictKicker'),
    verdictHeadline: document.getElementById('verdictHeadline'),
    verdictSub: document.getElementById('verdictSub'),

    fleaNetValue: document.getElementById('fleaNetValue'),
    fleaNetMeta: document.getElementById('fleaNetMeta'),
    buybackNetValue: document.getElementById('buybackNetValue'),
    buybackNetMeta: document.getElementById('buybackNetMeta'),

    barFleaAmount: document.getElementById('barFleaAmount'),
    barFleaNet: document.getElementById('barFleaNet'),
    barFleaCost: document.getElementById('barFleaCost'),
    barBuybackAmount: document.getElementById('barBuybackAmount'),
    barBuybackNet: document.getElementById('barBuybackNet'),
    barBuybackCost: document.getElementById('barBuybackCost'),

    breakevenList: document.getElementById('breakevenList'),
    profitSection: document.getElementById('profitSection'),
    profitFlea: document.getElementById('profitFlea'),
    profitBuyback: document.getElementById('profitBuyback'),

    platformTableBody: document.getElementById('platformTableBody'),
    recContainer: document.getElementById('sellRecBox'),
    shareBtn: document.getElementById('sellShareBtn'),
    copyBtn: document.getElementById('sellCopyBtn'),
    copyToast: document.getElementById('sellCopyToast'),
  };

  if (!el.fleaPrice) return;

  // プラットフォーム選択肢を生成
  el.platformSelect.innerHTML =
    PLATFORM_PRESETS.map(
      (p) => `<option value="${p.id}">${escapeHtml(p.name)}（${(p.feeRate * 100).toFixed(p.feeRate * 100 % 1 === 0 ? 0 : 1)}%）</option>`
    ).join('') + '<option value="custom">カスタム手数料率</option>';

  // 送料選択肢を生成
  el.shippingPreset.innerHTML = SHIPPING_PRESETS.map(
    (s) => `<option value="${s.id}">${escapeHtml(s.label)}</option>`
  ).join('');

  // デフォルトを「未開封BOX（1箱）」にセット
  function applyItemPreset(presetKey, overwritePrices = true) {
    const preset = ITEM_TYPE_PRESETS[presetKey];
    if (!preset) return;
    el.presetButtons.forEach((btn) => {
      btn.classList.toggle('is-active', btn.dataset.itemPreset === presetKey);
    });
    el.shippingPreset.value = preset.shippingPreset;
    el.shippingCost.value = String(preset.shippingCost);
    el.packingCost.value = String(preset.packingCost);
    if (overwritePrices) {
      el.fleaPrice.value = String(preset.defaultFleaPrice);
      el.buybackPrice.value = String(preset.defaultBuybackPrice);
    }
  }

  // URLパラメータから初期値を受け取る（portfolio.html からの連携用）
  const params = new URLSearchParams(window.location.search);
  const queryType = params.get('type');
  const queryFlea = params.get('flea');
  const queryBuyback = params.get('buyback');
  const queryCost = params.get('cost');
  const queryName = params.get('name');

  if (queryType && ITEM_TYPE_PRESETS[queryType]) {
    applyItemPreset(queryType, !queryFlea);
  } else {
    applyItemPreset('box', !queryFlea);
  }

  if (queryName && el.itemName) el.itemName.value = queryName;
  if (queryFlea) el.fleaPrice.value = String(Math.max(0, Number(queryFlea) || 0));
  if (queryBuyback) {
    el.buybackPrice.value = String(Math.max(0, Number(queryBuyback) || 0));
  } else if (queryFlea) {
    // フリマ価格だけ渡された場合は目安として85%を買取査定に仮セット
    el.buybackPrice.value = String(Math.round((Number(queryFlea) || 0) * 0.85 / 100) * 100);
  }
  if (queryCost && el.purchaseCost) el.purchaseCost.value = String(Math.max(0, Number(queryCost) || 0));

  el.platformSelect.value = 'mercari';
  el.feeRate.value = '10';

  let lastSummaryText = '';

  function getSelectedPlatformName() {
    const found = PLATFORM_PRESETS.find((p) => p.id === el.platformSelect.value);
    return found ? found.name : 'フリマ';
  }

  function update() {
    const feeRatePct = Math.max(0, Math.min(95, Number(el.feeRate.value) || 0));
    const effort = Number(el.effortCost.value) || 0;
    if (el.effortCostLabel) {
      el.effortCostLabel.textContent = effort > 0 ? `${formatYen(effort)}（手間考慮）` : '0円（純粋な手取り比較）';
    }

    const res = calculateSellComparison({
      fleaPrice: el.fleaPrice.value,
      platformFeeRate: feeRatePct / 100,
      shippingCost: el.shippingCost.value,
      packingCost: el.packingCost.value,
      buybackPrice: el.buybackPrice.value,
      buybackCost: el.buybackCost.value,
      purchaseCost: el.purchaseCost ? el.purchaseCost.value : 0,
      effortCost: effort,
    });

    const platformName = getSelectedPlatformName();
    const itemLabel = el.itemName && el.itemName.value.trim() ? `「${el.itemName.value.trim()}」` : '';

    // 結論バナー更新
    el.verdictBox.className = 'verdict-box';
    if (res.fleaPrice === 0 && res.buybackPrice === 0) {
      el.verdictKicker.textContent = '価格を入力してください';
      el.verdictHeadline.textContent = 'フリマ価格と買取査定額を比較します';
      el.verdictSub.textContent = '手数料・送料・梱包費を自動で差し引いて実質手取りを算出します。';
    } else if (res.winner === 'flea') {
      el.verdictBox.classList.add('is-positive');
      el.verdictKicker.textContent = res.isCloseCall ? '僅差でフリマ優位（手間も要検討）' : 'おすすめ売却先：フリマ出品';
      el.verdictHeadline.textContent = `${platformName}の方が ${formatYen(Math.abs(res.rawDiff))} 手取りが多い`;
      el.verdictSub.textContent =
        effort > 0
          ? `出品の手間（${formatYen(effort)}）を差し引いても実質 ${formatYen(res.effectiveDiff, { signed: true })} お得です。`
          : res.isCloseCall
            ? 'ただし差額は300円以内です。即日現金化や梱包の手間を考えると買取店も有力です。'
            : `手数料 ${formatYen(res.platformFee)}・送料/梱包 ${formatYen(res.shippingCost + res.packingCost)} を引いても買取店を上回ります。`;
    } else if (res.winner === 'buyback') {
      el.verdictBox.classList.add('is-gold');
      el.verdictKicker.textContent = 'おすすめ売却先：買取店（店頭・宅配）';
      if (res.rawDiff < 0) {
        el.verdictHeadline.textContent = `買取店の方が ${formatYen(Math.abs(res.rawDiff))} 手取りが多い`;
        el.verdictSub.textContent = `${platformName}の手数料・送料を引くと買取査定を下回ります。手間なく高値で売れる買取店が明確にお得です。`;
      } else {
        el.verdictHeadline.textContent = `手間込みなら買取店が実質 ${formatYen(Math.abs(res.effectiveDiff))} お得`;
        el.verdictSub.textContent = `純粋な手取り差は ${formatYen(res.rawDiff)} ですが、出品・発送の手間（${formatYen(effort)}）を考慮すると買取店が合理的です。`;
      }
    } else {
      el.verdictKicker.textContent = '手取りは同額';
      el.verdictHeadline.textContent = `${platformName}と買取店はほぼ同額`;
      el.verdictSub.textContent = '同額なら、値下げ交渉や発送トラブルのない買取店がスムーズです。';
    }

    // KPIカード更新
    el.fleaNetValue.textContent = formatYen(res.fleaNet);
    el.fleaNetValue.className = `kpi-value num ${res.fleaNet >= res.buybackNet ? 'is-positive' : ''}`;
    el.fleaNetMeta.textContent = `手数料 ${formatYen(res.platformFee)} ＋ 送料/梱包 ${formatYen(res.shippingCost + res.packingCost)}`;

    el.buybackNetValue.textContent = formatYen(res.buybackNet);
    el.buybackNetValue.className = `kpi-value num ${res.buybackNet > res.fleaNet ? 'is-gold' : ''}`;
    el.buybackNetMeta.textContent =
      res.buybackCost > 0 ? `査定額 ${formatYen(res.buybackPrice)} − 諸費用 ${formatYen(res.buybackCost)}` : `査定額そのまま手取り（諸費用 0円）`;

    // 比較バー更新
    const maxScale = Math.max(res.fleaPrice, res.buybackPrice, 1);
    const fleaNetPct = Math.max(0, (Math.max(0, res.fleaNet) / maxScale) * 100);
    const fleaCostPct = Math.max(0, (res.fleaTotalCost / maxScale) * 100);
    const buyNetPct = Math.max(0, (Math.max(0, res.buybackNet) / maxScale) * 100);
    const buyCostPct = Math.max(0, (res.buybackCost / maxScale) * 100);

    el.barFleaAmount.textContent = `${formatYen(res.fleaNet)}（出品 ${formatYen(res.fleaPrice)}）`;
    el.barFleaNet.style.width = `${Math.min(100, fleaNetPct)}%`;
    el.barFleaCost.style.width = `${Math.min(100 - Math.min(100, fleaNetPct), fleaCostPct)}%`;

    el.barBuybackAmount.textContent = `${formatYen(res.buybackNet)}（査定 ${formatYen(res.buybackPrice)}）`;
    el.barBuybackNet.style.width = `${Math.min(100, buyNetPct)}%`;
    el.barBuybackCost.style.width = `${Math.min(100 - Math.min(100, buyNetPct), buyCostPct)}%`;

    // 損益分岐点逆算
    const effortNote =
      effort > 0
        ? `（手間 ${formatYen(effort)} 込みだと <strong>${formatYen(res.breakEvenFleaPriceWithEffort)}以上</strong>）`
        : '';
    el.breakevenList.innerHTML = `
      <li>買取査定（<strong>${formatYen(res.buybackPrice)}</strong>）を上回るには、${escapeHtml(platformName)}で <strong>${formatYen(res.breakEvenFleaPriceRaw)}以上</strong> で売る必要があります${effortNote}。</li>
      <li>${escapeHtml(platformName)}相場（<strong>${formatYen(res.fleaPrice)}</strong>）に対して、買取店の査定が <strong>${formatYen(res.breakEvenBuybackPrice)}以上</strong> なら買取店の方がお得です。</li>
    `;

    // 仕入れ原価がある場合の純利益・ROI
    if (el.profitSection) {
      el.profitSection.hidden = !res.hasPurchaseCost;
      if (res.hasPurchaseCost) {
        el.profitFlea.textContent = `${formatYen(res.fleaProfit, { signed: true })}（ROI ${formatPercent(res.fleaRoi, { signed: true })}）`;
        el.profitFlea.className = `kpi-value num ${res.fleaProfit >= 0 ? 'is-positive' : 'is-negative'}`;
        el.profitBuyback.textContent = `${formatYen(res.buybackProfit, { signed: true })}（ROI ${formatPercent(res.buybackRoi, { signed: true })}）`;
        el.profitBuyback.className = `kpi-value num ${res.buybackProfit >= 0 ? 'is-positive' : 'is-negative'}`;
      }
    }

    // 横断比較テーブル（存在する場合）
    if (el.platformTableBody) {
      const topNet = res.platformComparisons[0]?.net ?? 0;
      el.platformTableBody.innerHTML = res.platformComparisons
        .map((row) => {
          const isBest = row.net === topNet && topNet > 0;
          const feeLabel = row.isBuyback
            ? row.fee > 0
              ? `諸費用 ${formatYen(row.fee)}`
              : '0円'
            : `${(row.feeRate * 100).toFixed(row.feeRate * 100 % 1 === 0 ? 0 : 1)}% (${formatYen(row.fee)})`;
          const diffLabel = row.isBuyback
            ? '基準'
            : formatYen(row.diffVsBuyback, { signed: true });
          const diffClass = row.isBuyback
            ? ''
            : row.diffVsBuyback > 0
              ? 'is-positive'
              : row.diffVsBuyback < 0
                ? 'is-negative'
                : '';
          return `
            <tr class="${isBest ? 'is-best' : ''}">
              <td>
                <strong>${escapeHtml(row.name)}</strong>
                ${isBest ? '<span class="badge badge-brand">最高手取り</span>' : ''}
              </td>
              <td class="num-cell">${feeLabel}</td>
              <td class="num-cell"><strong>${formatYen(row.net)}</strong></td>
              <td class="num-cell"><span class="kpi-meta ${diffClass}" style="font-weight:700;font-size:0.86rem;">${diffLabel}</span></td>
              <td class="num-cell">${row.isBuyback ? '—' : `${formatYen(row.breakEven)}〜`}</td>
            </tr>
          `;
        })
        .join('');
    }

    // 結果連動のおすすめアクション（収益化動線）
    if (res.winner === 'buyback' || res.isCloseCall) {
      renderContextualRecommendation(el.recContainer, {
        category: 'buyback',
        title: '買取店が有利なときの手取りアップ術',
        fallbackTip:
          '店舗ごとに未開封BOXや高額シングルの買取価格は5〜20%ほど差が出ます。複数店の査定額を比べるか、宅配買取のまとめ売りキャンペーンを活用すると手取りをさらに伸ばせます。',
      });
    } else {
      renderContextualRecommendation(el.recContainer, {
        category: 'supplies',
        title: 'フリマ出品で利益をさらに残すコツ',
        fallbackTip:
          '同じ出品額でも、Yahoo!フリマ（手数料5%）を併用するとメルカリ（10%）より手数料を半減できます。またローダーや専用封筒をまとめ買いしておくと、1件あたりの梱包コストを50円以下に抑えられます。',
      });
    }

    // シェアテキスト更新
    const winnerText =
      res.winner === 'flea'
        ? `${platformName}の方が${formatYen(Math.abs(res.rawDiff))}お得`
        : res.winner === 'buyback'
          ? `買取店の方が${res.rawDiff < 0 ? formatYen(Math.abs(res.rawDiff)) : `手間込み実質${formatYen(Math.abs(res.effectiveDiff))}`}お得`
          : 'ほぼ同額';

    lastSummaryText = `${itemLabel}売却比較：${platformName} ${formatYen(res.fleaPrice)}（手取り${formatYen(res.fleaNet)}） vs 買取 ${formatYen(res.buybackPrice)}（手取り${formatYen(res.buybackNet)}）→ ${winnerText}！ 損益分岐ラインは${platformName}${formatYen(res.breakEvenFleaPriceRaw)}。`;

    if (el.shareBtn) {
      el.shareBtn.href = buildXShareUrl(lastSummaryText, 'sell-compare.html');
    }
  }

  // イベントバインド
  el.presetButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      applyItemPreset(btn.dataset.itemPreset, true);
      update();
    });
  });

  el.platformSelect.addEventListener('change', () => {
    const found = PLATFORM_PRESETS.find((p) => p.id === el.platformSelect.value);
    if (found) {
      el.feeRate.value = String(Number((found.feeRate * 100).toFixed(2)));
    }
    update();
  });

  el.feeRate.addEventListener('input', () => {
    el.platformSelect.value = 'custom';
    update();
  });

  el.shippingPreset.addEventListener('change', () => {
    const found = SHIPPING_PRESETS.find((s) => s.id === el.shippingPreset.value);
    if (found && found.cost !== null) {
      el.shippingCost.value = String(found.cost);
    }
    update();
  });

  el.shippingCost.addEventListener('input', () => {
    el.shippingPreset.value = 'custom';
    update();
  });

  [
    el.itemName,
    el.fleaPrice,
    el.packingCost,
    el.buybackPrice,
    el.buybackCost,
    el.purchaseCost,
    el.effortCost,
  ]
    .filter(Boolean)
    .forEach((input) => input.addEventListener('input', update));

  if (el.copyBtn) {
    el.copyBtn.addEventListener('click', () => {
      copyTextWithToast(lastSummaryText, el.copyToast);
    });
  }

  update();
}
