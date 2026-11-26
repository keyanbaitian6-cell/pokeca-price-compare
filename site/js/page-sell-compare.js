/**
 * ツール1 V2: フリマ vs 買取店 手取り最大比較コントローラー
 * - ファーストビュー2入力で即判定＋モバイル下部スティッキー結果バー
 * - 詳細設定アコーディオン（送料・梱包・振込手数料・仕入れ値・手間コスト）
 * - 全6フリマ＋買取店 ランキングカード＆値下げ交渉シミュレーター
 * - 入力値のブラウザ自動記憶（localStorage）＆ポートフォリオからのURL引き継ぎ
 */
import {
  ITEM_TYPE_PRESETS,
  PLATFORM_PRESETS,
  SHIPPING_PRESETS,
  calculateSellComparison,
} from './calculators.js';
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

const STORAGE_KEY = 'tcg_profit_lab_sell_v2';

export function initSellComparePage(activePageId = 'home') {
  initCommonChrome(activePageId);

  const el = {
    presetButtons: document.querySelectorAll('[data-item-preset]'),
    stepButtons: document.querySelectorAll('[data-step-target]'),
    resetBtn: document.getElementById('sellResetBtn'),

    itemName: document.getElementById('sellItemName'),
    fleaPrice: document.getElementById('fleaPrice'),
    buybackPrice: document.getElementById('buybackPrice'),

    settingsSummary: document.getElementById('sellSettingsSummary'),
    platformSelect: document.getElementById('platformSelect'),
    feeRate: document.getElementById('feeRate'),
    shippingPreset: document.getElementById('shippingPreset'),
    shippingCost: document.getElementById('shippingCost'),
    packingCost: document.getElementById('packingCost'),
    includeWithdrawalFee: document.getElementById('includeWithdrawalFee'),
    buybackCost: document.getElementById('buybackCost'),
    purchaseCost: document.getElementById('purchaseCost'),
    effortCost: document.getElementById('effortCost'),
    effortCostLabel: document.getElementById('effortCostLabel'),

    verdictCard: document.getElementById('verdictBox'),
    verdictKicker: document.getElementById('verdictKicker'),
    verdictBadge: document.getElementById('verdictBadge'),
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

    rankList: document.getElementById('platformRankList'),
    priceDropBody: document.getElementById('priceDropTableBody'),
    recContainer: document.getElementById('sellRecBox'),
    shareBtn: document.getElementById('sellShareBtn'),
    copyBtn: document.getElementById('sellCopyBtn'),
    copyToast: document.getElementById('sellCopyToast'),

    stickyBar: document.getElementById('stickyVerdictBar'),
    stickyTitle: document.getElementById('stickyVerdictTitle'),
    stickySub: document.getElementById('stickyVerdictSub'),
  };

  if (!el.fleaPrice) return;

  el.platformSelect.innerHTML =
    PLATFORM_PRESETS.map((p) => {
      const pct = (p.feeRate * 100).toFixed((p.feeRate * 100) % 1 === 0 ? 0 : 1);
      return `<option value="${p.id}">${escapeHtml(p.name)}（${pct}%）</option>`;
    }).join('') + '<option value="custom">カスタム手数料率</option>';

  el.shippingPreset.innerHTML = SHIPPING_PRESETS.map(
    (s) => `<option value="${s.id}">${escapeHtml(s.label)}</option>`
  ).join('');

  let currentItemPreset = 'box';

  function applyItemPreset(presetKey, overwritePrices = true) {
    const preset = ITEM_TYPE_PRESETS[presetKey];
    if (!preset) return;
    currentItemPreset = presetKey;
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

  function getSelectedPlatform() {
    return PLATFORM_PRESETS.find((p) => p.id === el.platformSelect.value) || null;
  }

  function restoreInitialState() {
    const params = new URLSearchParams(window.location.search);
    const hasQuery = params.has('flea') || params.has('buyback') || params.has('type');

    if (hasQuery) {
      const qType = params.get('type');
      applyItemPreset(ITEM_TYPE_PRESETS[qType] ? qType : 'box', !params.has('flea'));
      if (params.get('name') && el.itemName) el.itemName.value = params.get('name');
      if (params.has('flea')) el.fleaPrice.value = String(Math.max(0, Number(params.get('flea')) || 0));
      if (params.has('buyback')) {
        el.buybackPrice.value = String(Math.max(0, Number(params.get('buyback')) || 0));
      } else if (params.has('flea')) {
        el.buybackPrice.value = String(Math.round(((Number(params.get('flea')) || 0) * 0.85) / 100) * 100);
      }
      if (params.has('cost') && el.purchaseCost) {
        el.purchaseCost.value = String(Math.max(0, Number(params.get('cost')) || 0));
      }
      el.platformSelect.value = 'mercari';
      el.feeRate.value = '10';
      return;
    }

    const saved = loadJsonState(STORAGE_KEY);
    if (saved && typeof saved === 'object') {
      applyItemPreset(ITEM_TYPE_PRESETS[saved.itemPreset] ? saved.itemPreset : 'box', false);
      el.fleaPrice.value = String(saved.fleaPrice ?? 12000);
      el.buybackPrice.value = String(saved.buybackPrice ?? 10500);
      el.platformSelect.value = saved.platformId || 'mercari';
      el.feeRate.value = String(saved.feeRate ?? 10);
      el.shippingPreset.value = saved.shippingPreset || 'takkyubin_compact';
      el.shippingCost.value = String(saved.shippingCost ?? 520);
      el.packingCost.value = String(saved.packingCost ?? 120);
      if (el.includeWithdrawalFee) el.includeWithdrawalFee.checked = Boolean(saved.includeWithdrawalFee);
      el.buybackCost.value = String(saved.buybackCost ?? 0);
      if (el.purchaseCost) el.purchaseCost.value = String(saved.purchaseCost ?? 0);
      el.effortCost.value = String(saved.effortCost ?? 0);
      if (el.itemName) el.itemName.value = saved.itemName || '';
      return;
    }

    applyItemPreset('box', true);
    el.platformSelect.value = 'mercari';
    el.feeRate.value = '10';
  }

  let lastSummaryText = '';

  function persistState() {
    saveJsonState(STORAGE_KEY, {
      itemPreset: currentItemPreset,
      fleaPrice: Number(el.fleaPrice.value) || 0,
      buybackPrice: Number(el.buybackPrice.value) || 0,
      platformId: el.platformSelect.value,
      feeRate: Number(el.feeRate.value) || 0,
      shippingPreset: el.shippingPreset.value,
      shippingCost: Number(el.shippingCost.value) || 0,
      packingCost: Number(el.packingCost.value) || 0,
      includeWithdrawalFee: el.includeWithdrawalFee ? el.includeWithdrawalFee.checked : false,
      buybackCost: Number(el.buybackCost.value) || 0,
      purchaseCost: el.purchaseCost ? Number(el.purchaseCost.value) || 0 : 0,
      effortCost: Number(el.effortCost.value) || 0,
      itemName: el.itemName ? el.itemName.value : '',
    });
  }

  function update() {
    const selectedPlatform = getSelectedPlatform();
    const platformName = selectedPlatform ? selectedPlatform.name : 'フリマ';
    const feeRatePct = Math.max(0, Math.min(95, Number(el.feeRate.value) || 0));
    const includeWithdrawal = el.includeWithdrawalFee ? el.includeWithdrawalFee.checked : false;
    const withdrawalFee = selectedPlatform ? selectedPlatform.withdrawalFee : 200;
    const effort = Number(el.effortCost.value) || 0;

    if (el.effortCostLabel) {
      el.effortCostLabel.textContent = effort > 0 ? `${formatYen(effort)}（手間考慮）` : '0円（純粋な手取り比較）';
    }

    const res = calculateSellComparison({
      fleaPrice: el.fleaPrice.value,
      platformFeeRate: feeRatePct / 100,
      shippingCost: el.shippingCost.value,
      packingCost: el.packingCost.value,
      includeWithdrawalFee: includeWithdrawal,
      withdrawalFee,
      buybackPrice: el.buybackPrice.value,
      buybackCost: el.buybackCost.value,
      purchaseCost: el.purchaseCost ? el.purchaseCost.value : 0,
      effortCost: effort,
    });

    // 詳細アコーディオンの1行サマリー更新
    if (el.settingsSummary) {
      const shipObj = SHIPPING_PRESETS.find((s) => s.id === el.shippingPreset.value);
      const shipText = shipObj && shipObj.cost !== null ? shipObj.shortLabel : `送料${formatYen(res.shippingCost)}`;
      const parts = [
        `${platformName}${feeRatePct}%`,
        shipText,
        `梱包${res.packingCost}円`,
      ];
      if (includeWithdrawal) parts.push(`振込${res.withdrawalFee}円`);
      if (effort > 0) parts.push(`手間${effort}円`);
      el.settingsSummary.textContent = parts.join('・');
    }

    // 結論バナー更新
    el.verdictCard.className = 'verdict-card';
    let shortStickyHeadline = '';
    if (res.fleaPrice === 0 && res.buybackPrice === 0) {
      el.verdictKicker.textContent = '金額を入力して比較';
      el.verdictHeadline.textContent = '価格を入れると即判定します';
      el.verdictSub.textContent = '手数料・送料・梱包費を差し引いた手取り差を表示します。';
      if (el.verdictBadge) el.verdictBadge.hidden = true;
      shortStickyHeadline = '価格を入力してください';
    } else if (res.winner === 'flea') {
      el.verdictCard.classList.add('is-flea');
      el.verdictKicker.textContent = res.isCloseCall ? '僅差でフリマ優位' : 'おすすめ売却先';
      el.verdictHeadline.textContent = `${platformName}の方が ${formatYen(Math.abs(res.rawDiff))} お得`;
      el.verdictSub.textContent =
        effort > 0
          ? `手間換算 ${formatYen(effort)} を引いても実質 ${formatYen(res.effectiveDiff, { signed: true })} プラス。`
          : res.isCloseCall
            ? '差額300円以内の接戦。発送や値下げの手間を省くなら買取店も有力です。'
            : `コスト計 ${formatYen(res.fleaTotalCost)} を引いても買取査定を上回ります。`;
      if (el.verdictBadge) {
        el.verdictBadge.hidden = false;
        el.verdictBadge.className = 'badge badge-brand';
        el.verdictBadge.textContent = 'フリマ有利';
      }
      shortStickyHeadline = `${platformName}が ${formatYen(Math.abs(res.rawDiff))} お得`;
    } else if (res.winner === 'buyback') {
      el.verdictCard.classList.add('is-buyback');
      el.verdictKicker.textContent = 'おすすめ売却先';
      if (res.rawDiff < 0) {
        el.verdictHeadline.textContent = `買取店の方が ${formatYen(Math.abs(res.rawDiff))} お得`;
        el.verdictSub.textContent = `${platformName}は手数料・送料で ${formatYen(res.fleaTotalCost)} 引かれるため、買取査定の方が手取りが多くなります。`;
        shortStickyHeadline = `買取店が ${formatYen(Math.abs(res.rawDiff))} お得`;
      } else {
        el.verdictHeadline.textContent = `手間込みなら買取店が ${formatYen(Math.abs(res.effectiveDiff))} お得`;
        el.verdictSub.textContent = `手取り差は ${formatYen(res.rawDiff)} ですが、出品の手間（${formatYen(effort)}）を考えると買取店が合理的です。`;
        shortStickyHeadline = `手間込みで買取店が有利`;
      }
      if (el.verdictBadge) {
        el.verdictBadge.hidden = false;
        el.verdictBadge.className = 'badge badge-gold';
        el.verdictBadge.textContent = '買取店有利';
      }
    } else {
      el.verdictKicker.textContent = '手取りは同額';
      el.verdictHeadline.textContent = `${platformName}と買取店は同額`;
      el.verdictSub.textContent = '同額なら即日現金化・クレームなしの買取店がスムーズです。';
      if (el.verdictBadge) {
        el.verdictBadge.hidden = false;
        el.verdictBadge.className = 'badge badge-muted';
        el.verdictBadge.textContent = '同額';
      }
      shortStickyHeadline = 'フリマと買取は同額';
    }

    // スティッキーモバイルバー更新
    if (el.stickyTitle) el.stickyTitle.textContent = shortStickyHeadline;
    if (el.stickySub) {
      el.stickySub.textContent = `${platformName}手取り ${formatYen(res.fleaNet)} ／ 買取 ${formatYen(res.buybackNet)}`;
    }

    // KPIカード更新
    el.fleaNetValue.textContent = formatYen(res.fleaNet);
    el.fleaNetValue.className = `kpi-value num ${res.fleaNet >= res.buybackNet ? 'is-positive' : ''}`;
    const wNote = res.withdrawalFee > 0 ? `＋振込${res.withdrawalFee}円` : '';
    el.fleaNetMeta.textContent = `手数料${formatYen(res.platformFee)}＋送料/梱包${formatYen(res.shippingCost + res.packingCost)}${wNote}`;

    el.buybackNetValue.textContent = formatYen(res.buybackNet);
    el.buybackNetValue.className = `kpi-value num ${res.buybackNet > res.fleaNet ? 'is-gold' : ''}`;
    el.buybackNetMeta.textContent =
      res.buybackCost > 0 ? `査定${formatYen(res.buybackPrice)} − 諸費用${formatYen(res.buybackCost)}` : '査定額そのまま手取り';

    // 比較バー更新
    const maxScale = Math.max(res.fleaPrice, res.buybackPrice, 1);
    const fleaNetPct = Math.max(0, (Math.max(0, res.fleaNet) / maxScale) * 100);
    const fleaCostPct = Math.max(0, (res.fleaTotalCost / maxScale) * 100);
    const buyNetPct = Math.max(0, (Math.max(0, res.buybackNet) / maxScale) * 100);
    const buyCostPct = Math.max(0, (res.buybackCost / maxScale) * 100);

    el.barFleaAmount.textContent = `${formatYen(res.fleaNet)} / 出品 ${formatYen(res.fleaPrice)}`;
    el.barFleaNet.style.width = `${Math.min(100, fleaNetPct)}%`;
    el.barFleaCost.style.width = `${Math.min(100 - Math.min(100, fleaNetPct), fleaCostPct)}%`;

    el.barBuybackAmount.textContent = `${formatYen(res.buybackNet)} / 査定 ${formatYen(res.buybackPrice)}`;
    el.barBuybackNet.style.width = `${Math.min(100, buyNetPct)}%`;
    el.barBuybackCost.style.width = `${Math.min(100 - Math.min(100, buyNetPct), buyCostPct)}%`;

    // 損益分岐点逆算
    el.breakevenList.innerHTML = `
      <li>買取店（<strong>${formatYen(res.buybackPrice)}</strong>）に勝つには、${escapeHtml(platformName)}で <strong>${formatYen(res.breakEvenFleaPriceRaw)}以上</strong> が必要</li>
      <li>今の${escapeHtml(platformName)}相場（<strong>${formatYen(res.fleaPrice)}</strong>）なら、買取査定 <strong>${formatYen(res.breakEvenBuybackPrice)}以上</strong> で買取店が逆転</li>
    `;

    // 仕入れ原価がある場合の純利益・ROI
    if (el.profitSection) {
      el.profitSection.hidden = !res.hasPurchaseCost;
      if (res.hasPurchaseCost) {
        el.profitFlea.textContent = `${formatYen(res.fleaProfit, { signed: true })}（${formatPercent(res.fleaRoi, { signed: true })}）`;
        el.profitFlea.className = `kpi-value num ${res.fleaProfit >= 0 ? 'is-positive' : 'is-negative'}`;
        el.profitBuyback.textContent = `${formatYen(res.buybackProfit, { signed: true })}（${formatPercent(res.buybackRoi, { signed: true })}）`;
        el.profitBuyback.className = `kpi-value num ${res.buybackProfit >= 0 ? 'is-positive' : 'is-negative'}`;
      }
    }

    // 6フリマ＋買取店 ランキングカード（スマホでも横スクロール不要！）
    if (el.rankList) {
      const topNet = res.platformComparisons[0]?.net ?? 0;
      el.rankList.innerHTML = res.platformComparisons
        .map((row, idx) => {
          const isTop = idx === 0 && topNet > 0;
          const feePctLabel = row.isBuyback
            ? row.fee > 0
              ? `諸費用 ${formatYen(row.fee)}`
              : '手数料0円・即日現金化'
            : `手数料${(row.feeRate * 100).toFixed((row.feeRate * 100) % 1 === 0 ? 0 : 1)}% (${formatYen(row.fee)})${row.withdrawalFee > 0 ? `＋振込${row.withdrawalFee}円` : ''}`;
          const diffText = row.isBuyback
            ? '比較基準'
            : `買取比 ${formatYen(row.diffVsBuyback, { signed: true })}`;
          const diffCls = row.isBuyback
            ? 'is-gold'
            : row.diffVsBuyback > 0
              ? 'is-positive'
              : row.diffVsBuyback < 0
                ? 'is-negative'
                : '';

          return `
            <div class="rank-card ${isTop ? 'is-top' : ''} ${row.isBuyback ? 'is-buyback' : ''}">
              <div class="rank-left">
                <div class="rank-name-row">
                  <span class="rank-num">#${idx + 1}</span>
                  <span class="rank-name">${escapeHtml(row.name)}</span>
                  ${isTop ? '<span class="badge badge-brand">最高手取り</span>' : ''}
                  ${row.isBuyback ? '<span class="badge badge-gold">手間ゼロ</span>' : ''}
                </div>
                <div class="rank-detail">${feePctLabel}${row.isBuyback ? '' : ` ／ 分岐 ${formatYen(row.breakEven)}〜`}</div>
              </div>
              <div class="rank-right">
                <div class="rank-net">${formatYen(row.net)}</div>
                <div class="rank-diff ${diffCls}">${diffText}</div>
              </div>
            </div>
          `;
        })
        .join('');
    }

    // 値下げ交渉シミュレーター表
    if (el.priceDropBody) {
      el.priceDropBody.innerHTML = res.priceDropTable
        .map((row) => {
          const rowCls = row.beatsBuyback ? '' : 'is-loss';
          const statusBadge = row.beatsBuyback
            ? '<span class="badge badge-brand">フリマ有利</span>'
            : '<span class="badge badge-danger">買取が逆転</span>';
          return `
            <tr class="${rowCls}">
              <td>${row.drop === 0 ? '現在の出品価格' : `-${row.drop.toLocaleString('ja-JP')}円 値下げ`}</td>
              <td class="num-cell"><strong>${formatYen(row.price)}</strong></td>
              <td class="num-cell"><strong>${formatYen(row.net)}</strong></td>
              <td class="num-cell"><strong class="${row.diffVsBuyback > 0 ? 'is-positive' : 'is-negative'}">${formatYen(row.diffVsBuyback, { signed: true })}</strong></td>
              <td>${statusBadge}</td>
            </tr>
          `;
        })
        .join('');
    }

    // 文脈連動おすすめ枠
    if (res.winner === 'buyback' || res.isCloseCall) {
      renderContextualRecommendation(el.recContainer, {
        category: 'buyback',
        title: '買取店が有利なときの手取りアップ術',
        fallbackTip:
          '店舗によって未開封BOXや高額シングルの査定額は5〜20%差がつきます。複数店の買取表を比べるか、宅配買取のまとめ売りキャンペーンを活用するとさらに手取りを伸ばせます。',
      });
    } else {
      renderContextualRecommendation(el.recContainer, {
        category: 'supplies',
        title: 'フリマ出品で手取りをさらに残すコツ',
        fallbackTip:
          'Yahoo!フリマ（5%）やmagi（7%）を併売するとメルカリ（10%）より手数料を大きく削減できます。値下げ交渉が来たときは下の「値下げライン表」で買取店を下回らないか即チェックしましょう。',
      });
    }

    const itemLabel = el.itemName && el.itemName.value.trim() ? `「${el.itemName.value.trim()}」` : '';
    const winnerText =
      res.winner === 'flea'
        ? `${platformName}の方が${formatYen(Math.abs(res.rawDiff))}お得`
        : res.winner === 'buyback'
          ? `買取店の方が${res.rawDiff < 0 ? formatYen(Math.abs(res.rawDiff)) : `手間込み${formatYen(Math.abs(res.effectiveDiff))}`}お得`
          : 'ほぼ同額';

    lastSummaryText = `${itemLabel}売却比較：${platformName} ${formatYen(res.fleaPrice)}（手取り${formatYen(res.fleaNet)}） vs 買取 ${formatYen(res.buybackPrice)}（手取り${formatYen(res.buybackNet)}）→ ${winnerText}！損益分岐は${platformName}${formatYen(res.breakEvenFleaPriceRaw)}。`;

    if (el.shareBtn) {
      el.shareBtn.href = buildXShareUrl(lastSummaryText, activePageId === 'home' ? '' : 'sell-compare.html');
    }

    persistState();
  }

  // イベントバインド
  el.presetButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      applyItemPreset(btn.dataset.itemPreset, true);
      update();
    });
  });

  el.stepButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      const target = document.getElementById(btn.dataset.stepTarget);
      if (!target) return;
      const delta = Number(btn.dataset.stepDelta) || 0;
      const next = Math.max(0, (Number(target.value) || 0) + delta);
      target.value = String(next);
      update();
    });
  });

  if (el.resetBtn) {
    el.resetBtn.addEventListener('click', () => {
      applyItemPreset('box', true);
      el.platformSelect.value = 'mercari';
      el.feeRate.value = '10';
      if (el.includeWithdrawalFee) el.includeWithdrawalFee.checked = false;
      el.buybackCost.value = '0';
      if (el.purchaseCost) el.purchaseCost.value = '0';
      el.effortCost.value = '0';
      if (el.itemName) el.itemName.value = '';
      update();
    });
  }

  el.platformSelect.addEventListener('change', () => {
    const found = getSelectedPlatform();
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

  if (el.includeWithdrawalFee) {
    el.includeWithdrawalFee.addEventListener('change', update);
  }

  if (el.copyBtn) {
    el.copyBtn.addEventListener('click', () => copyTextWithToast(lastSummaryText, el.copyToast));
  }

  restoreInitialState();
  update();

  bindStickyMobileBar({
    targetEl: el.verdictCard,
    barEl: el.stickyBar,
    scrollToSelector: '#verdictBox',
  });
}
