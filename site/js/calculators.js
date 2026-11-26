/**
 * トレカ損益ラボ — 純粋計算エンジン（ES Module）
 * 2026年11月 公式手数料・送料・PSA日本支社料金準拠。外部依存ゼロ・APIキー不要。
 */

export const DATA_VERIFIED_LABEL = '2026年11月 公式確認';

export const PLATFORM_PRESETS = [
  {
    id: 'mercari',
    name: 'メルカリ',
    feeRate: 0.10,
    withdrawalFee: 200,
    note: '販売手数料10%・振込200円（売れやすさ最大）',
  },
  {
    id: 'yahoo_flea',
    name: 'Yahoo!フリマ',
    feeRate: 0.05,
    withdrawalFee: 0,
    note: '販売手数料5%・PayPay/PayPay銀行振込0円（他行100円）',
  },
  {
    id: 'magi',
    name: 'magi',
    feeRate: 0.07,
    withdrawalFee: 200,
    note: '販売手数料7%・振込200円（トレカ専門・あんしん取引）',
  },
  {
    id: 'snkrdunk',
    name: 'スニダン',
    feeRate: 0.095,
    withdrawalFee: 200,
    note: '販売手数料9.5%〜7.0%・振込200円（真贋鑑定付き）',
  },
  {
    id: 'yahoo_auction',
    name: 'Yahoo!オークション',
    feeRate: 0.10,
    withdrawalFee: 100,
    note: '落札手数料10%・振込100円（高額品・希少品向き）',
  },
  {
    id: 'rakuma',
    name: '楽天ラクマ',
    feeRate: 0.10,
    withdrawalFee: 210,
    note: '販売手数料10%〜4.5%（実績変動）・楽天銀行1万円以上無料',
  },
];

export const ITEM_TYPE_PRESETS = {
  box: {
    label: '未開封BOX',
    shippingCost: 520,
    packingCost: 120,
    shippingPreset: 'takkyubin_compact',
    // 12,000円出品は手数料1,200+送料520+梱包120=手取り10,160円 → 買取10,500円の逆転が一目で分かる定番例
    defaultFleaPrice: 12000,
    defaultBuybackPrice: 10500,
    exampleHint: '例：人気BOX（メルカリ12,000円 vs 買取10,500円）',
  },
  single: {
    label: 'シングル',
    shippingCost: 180,
    packingCost: 50,
    shippingPreset: 'yupacket_mini',
    defaultFleaPrice: 6000,
    defaultBuybackPrice: 4500,
    exampleHint: '例：SR/SARシングル（メルカリ6,000円 vs 買取4,500円）',
  },
  psa: {
    label: 'PSA鑑定品',
    shippingCost: 210,
    packingCost: 100,
    shippingPreset: 'nekopos',
    defaultFleaPrice: 28000,
    defaultBuybackPrice: 23000,
    exampleHint: '例：PSA10カード（メルカリ28,000円 vs 買取23,000円）',
  },
  bulk: {
    label: '複数BOX',
    shippingCost: 750,
    packingCost: 200,
    shippingPreset: 'takkyubin_60',
    defaultFleaPrice: 36000,
    defaultBuybackPrice: 32000,
    exampleHint: '例：未開封BOX×3箱（メルカリ36,000円 vs 買取32,000円）',
  },
};

export const SHIPPING_PRESETS = [
  { id: 'yupacket_mini', label: 'ゆうパケットポストmini（160円＋封筒20円＝180円）', shortLabel: 'ポストmini 180円', cost: 180 },
  { id: 'nekopos', label: 'ネコポス（210円・厚さ3cm以内）', shortLabel: 'ネコポス 210円', cost: 210 },
  { id: 'yupacket_post', label: 'ゆうパケットポスト（215円＋シール5円＝220円）', shortLabel: 'ポスト 220円', cost: 220 },
  { id: 'yupacket', label: 'ゆうパケット（230円・A4/厚さ3cm）', shortLabel: 'ゆうパケット 230円', cost: 230 },
  { id: 'takkyubin_compact', label: '宅急便コンパクト（450円＋専用BOX70円＝520円）', shortLabel: 'コンパクト 520円', cost: 520 },
  { id: 'yupacket_plus', label: 'ゆうパケットプラス（455円＋専用箱65円＝520円）', shortLabel: 'プラス 520円', cost: 520 },
  { id: 'takkyubin_60', label: '宅急便 60サイズ（750円）', shortLabel: '宅急便60 750円', cost: 750 },
  { id: 'takkyubin_80', label: '宅急便 80サイズ（850円）', shortLabel: '宅急便80 850円', cost: 850 },
  { id: 'custom', label: 'カスタム送料（直接入力）', shortLabel: 'カスタム送料', cost: null },
];

/**
 * 2026年11月 PSA日本支社 公式サービスレベル基準
 */
export const PSA_PLAN_PRESETS = [
  {
    id: 'jp_value',
    label: 'PSA日本支社 バリュー（5,980円｜申告8万円以下・目安24週）',
    shortLabel: 'バリュー 5,980円',
    fee: 5980,
    maxValue: 80000,
    eta: '約120営業日（約24週間）',
  },
  {
    id: 'jp_standard',
    label: 'PSA日本支社 スタンダード（9,980円｜申告15万円以下・目安20週）',
    shortLabel: 'スタンダード 9,980円',
    fee: 9980,
    maxValue: 150000,
    eta: '約100営業日（約20週間）',
  },
  {
    id: 'jp_priority',
    label: 'PSA日本支社 プライオリティ（11,980円｜申告25万円以下・目安16週）',
    shortLabel: 'プライオリティ 11,980円',
    fee: 11980,
    maxValue: 250000,
    eta: '約80営業日（約16週間）',
  },
  {
    id: 'jp_express',
    label: 'PSA日本支社 エクスプレス（29,980円｜申告40万円以下・目安5週）',
    shortLabel: 'エクスプレス 29,980円',
    fee: 29980,
    maxValue: 400000,
    eta: '約25営業日（約5週間）',
  },
  {
    id: 'proxy_est',
    label: '鑑定代行プラン目安（4,000円｜業者・為替で変動）',
    shortLabel: '代行目安 4,000円',
    fee: 4000,
    maxValue: 80000,
    eta: '業者により変動',
  },
  {
    id: 'custom',
    label: 'カスタム鑑定料（直接入力）',
    shortLabel: 'カスタム',
    fee: null,
    maxValue: null,
    eta: '—',
  },
];

export const POPULAR_POKECA_BOXES = [
  'ポケモンカード151',
  'テラスタルフェスex',
  'バトルパートナーズ',
  '熱風のアリーナ',
  'ロケット団の栄光',
  'ブラックボルト',
  'ホワイトフレア',
  'クレイバースト',
  'VSTARユニバース',
  'イーブイヒーローズ',
  'シャイニートレジャーex',
  '超電ブレイカー',
  '楽園ドラゴーナ',
  'ロストアビス',
  '蒼空ストリーム',
  '25th ANNIVERSARY COLLECTION',
];

function clampNumber(value, min = 0, max = Number.POSITIVE_INFINITY) {
  const n = Number(value);
  if (!Number.isFinite(n)) return min;
  return Math.min(Math.max(n, min), max);
}

/**
 * 切り捨て手数料を考慮した正確な損益分岐出品価格を求める
 * P - Math.floor(P * feeRate) - fixedCosts >= targetNet
 */
export function solveBreakEvenSellingPrice(targetNet, feeRate, fixedCosts = 0) {
  const rate = clampNumber(feeRate, 0, 0.99);
  const required = targetNet + fixedCosts;
  if (required <= 0) return 0;

  let price = Math.ceil(required / (1 - rate));
  while (price > 0 && (price - 1) - Math.floor((price - 1) * rate) - fixedCosts >= targetNet) {
    price -= 1;
  }
  while (price - Math.floor(price * rate) - fixedCosts < targetNet) {
    price += 1;
  }
  return price;
}

/**
 * ツール1: フリマ vs 買取店 手取り・損益分岐点・値下げ交渉シミュレーター計算
 */
export function calculateSellComparison(input) {
  const fleaPrice = Math.round(clampNumber(input.fleaPrice, 0));
  const platformFeeRate = clampNumber(input.platformFeeRate, 0, 0.95);
  const shippingCost = Math.round(clampNumber(input.shippingCost, 0));
  const packingCost = Math.round(clampNumber(input.packingCost, 0));
  const includeWithdrawalFee = Boolean(input.includeWithdrawalFee);
  const withdrawalFee = includeWithdrawalFee
    ? Math.round(clampNumber(input.withdrawalFee ?? 200, 0))
    : 0;
  const buybackPrice = Math.round(clampNumber(input.buybackPrice, 0));
  const buybackCost = Math.round(clampNumber(input.buybackCost, 0));
  const purchaseCost = Math.round(clampNumber(input.purchaseCost, 0));
  const effortCost = Math.round(clampNumber(input.effortCost, 0));

  const platformFee = Math.floor(fleaPrice * platformFeeRate);
  const fixedFleaCosts = shippingCost + packingCost + withdrawalFee;
  const fleaTotalCost = platformFee + fixedFleaCosts;
  const fleaNet = fleaPrice - fleaTotalCost;
  const buybackNet = buybackPrice - buybackCost;

  const rawDiff = fleaNet - buybackNet;
  const effectiveFleaNet = fleaNet - effortCost;
  const effectiveDiff = effectiveFleaNet - buybackNet;

  let winner = 'tie';
  if (effectiveDiff > 0) {
    winner = 'flea';
  } else if (effectiveDiff < 0) {
    winner = 'buyback';
  }

  const isCloseCall = Math.abs(rawDiff) <= 300 && buybackPrice > 0 && fleaPrice > 0;

  // 損益分岐点（逆算）
  const breakEvenFleaPriceRaw = solveBreakEvenSellingPrice(
    buybackNet,
    platformFeeRate,
    fixedFleaCosts
  );
  const breakEvenFleaPriceWithEffort = solveBreakEvenSellingPrice(
    buybackNet + effortCost,
    platformFeeRate,
    fixedFleaCosts
  );
  const breakEvenBuybackPrice = Math.max(0, fleaNet + buybackCost);

  // 仕入れ原価がある場合の純利益・ROI
  const hasPurchaseCost = purchaseCost > 0;
  const fleaProfit = hasPurchaseCost ? fleaNet - purchaseCost : null;
  const buybackProfit = hasPurchaseCost ? buybackNet - purchaseCost : null;
  const fleaRoi = hasPurchaseCost ? (fleaProfit / purchaseCost) * 100 : null;
  const buybackRoi = hasPurchaseCost ? (buybackProfit / purchaseCost) * 100 : null;

  // 値下げ交渉シミュレーション（現在出品額から段階値下げしたとき買取店に勝てるか）
  const dropSteps = fleaPrice >= 20000
    ? [0, 500, 1000, 2000, 3000]
    : fleaPrice >= 5000
      ? [0, 300, 500, 1000, 1500]
      : [0, 100, 200, 300, 500];

  const priceDropTable = dropSteps
    .map((drop) => Math.max(0, fleaPrice - drop))
    .filter((p, idx, arr) => idx === 0 || (p > 0 && p !== arr[idx - 1]))
    .map((price) => {
      const drop = fleaPrice - price;
      const fee = Math.floor(price * platformFeeRate);
      const net = price - fee - fixedFleaCosts;
      const diffVsBuyback = net - buybackNet;
      return {
        drop,
        price,
        fee,
        net,
        diffVsBuyback,
        beatsBuyback: diffVsBuyback > 0,
      };
    });

  // 全6フリマ・買取店 横断比較リスト
  const platformComparisons = PLATFORM_PRESETS.map((p) => {
    const fee = Math.floor(fleaPrice * p.feeRate);
    const wFee = includeWithdrawalFee ? p.withdrawalFee : 0;
    const net = fleaPrice - fee - shippingCost - packingCost - wFee;
    const diffVsBuyback = net - buybackNet;
    const breakEven = solveBreakEvenSellingPrice(
      buybackNet,
      p.feeRate,
      shippingCost + packingCost + wFee
    );
    return {
      id: p.id,
      name: p.name,
      feeRate: p.feeRate,
      fee,
      withdrawalFee: wFee,
      net,
      diffVsBuyback,
      breakEven,
      isBuyback: false,
      note: p.note,
    };
  });

  platformComparisons.push({
    id: 'buyback',
    name: '買取店（店頭・宅配）',
    feeRate: 0,
    fee: buybackCost,
    withdrawalFee: 0,
    net: buybackNet,
    diffVsBuyback: 0,
    breakEven: breakEvenBuybackPrice,
    isBuyback: true,
    note: '即日現金化・値下げ交渉/発送トラブルなし',
  });

  platformComparisons.sort((a, b) => b.net - a.net);

  return {
    fleaPrice,
    platformFeeRate,
    platformFee,
    shippingCost,
    packingCost,
    includeWithdrawalFee,
    withdrawalFee,
    fleaTotalCost,
    fleaNet,
    buybackPrice,
    buybackCost,
    buybackNet,
    effortCost,
    effectiveFleaNet,
    rawDiff,
    effectiveDiff,
    winner,
    isCloseCall,
    breakEvenFleaPriceRaw,
    breakEvenFleaPriceWithEffort,
    breakEvenBuybackPrice,
    hasPurchaseCost,
    purchaseCost,
    fleaProfit,
    buybackProfit,
    fleaRoi,
    buybackRoi,
    priceDropTable,
    platformComparisons,
  };
}

/**
 * ツール2: PSA鑑定 損益分岐点＆期待値シミュレーター
 */
export function calculatePsaSimulation(input) {
  const rawCardCost = Math.round(clampNumber(input.rawCardCost, 0));
  const gradingFeePerCard = Math.round(clampNumber(input.gradingFeePerCard, 0));
  const cardCount = Math.max(1, Math.round(clampNumber(input.cardCount, 1, 500)));
  const totalShippingCost = Math.round(clampNumber(input.totalShippingCost, 0));
  const sellFeeRate = clampNumber(input.sellFeeRate, 0, 0.95);
  const sellShippingPerCard = Math.round(clampNumber(input.sellShippingPerCard, 0));

  const pricePsa10 = Math.round(clampNumber(input.pricePsa10, 0));
  const pricePsa9 = Math.round(clampNumber(input.pricePsa9, 0));
  const pricePsa8OrLower = Math.round(clampNumber(input.pricePsa8OrLower, 0));

  const probPsa10 = clampNumber(input.probPsa10, 0, 100);
  const remaining = Math.max(0, 100 - probPsa10);
  const rawProb9 = input.probPsa9 !== undefined ? clampNumber(input.probPsa9, 0, remaining) : Math.round(remaining * 0.85);
  const probPsa9 = Math.min(rawProb9, remaining);
  const probPsa8OrLower = Math.max(0, 100 - probPsa10 - probPsa9);

  const shippingPerCard = Math.round(totalShippingCost / cardCount);
  const totalCostPerCard = rawCardCost + gradingFeePerCard + shippingPerCard;

  const netFromSale = (price) => price - Math.floor(price * sellFeeRate) - sellShippingPerCard;

  const net10 = netFromSale(pricePsa10);
  const net9 = netFromSale(pricePsa9);
  const net8 = netFromSale(pricePsa8OrLower);

  const profit10 = net10 - totalCostPerCard;
  const profit9 = net9 - totalCostPerCard;
  const profit8 = net8 - totalCostPerCard;

  const roi10 = totalCostPerCard > 0 ? (profit10 / totalCostPerCard) * 100 : 0;
  const roi9 = totalCostPerCard > 0 ? (profit9 / totalCostPerCard) * 100 : 0;
  const roi8 = totalCostPerCard > 0 ? (profit8 / totalCostPerCard) * 100 : 0;

  const p10 = probPsa10 / 100;
  const p9 = probPsa9 / 100;
  const p8 = probPsa8OrLower / 100;

  const expectedNetPerCard = Math.round(p10 * net10 + p9 * net9 + p8 * net8);
  const expectedProfitPerCard = Math.round(p10 * profit10 + p9 * profit9 + p8 * profit8);
  const expectedTotalProfit = expectedProfitPerCard * cardCount;
  const expectedRoi = totalCostPerCard > 0 ? (expectedProfitPerCard / totalCostPerCard) * 100 : 0;

  const rawSaleNet = netFromSale(rawCardCost);
  const advantageOverRawSale = expectedNetPerCard - gradingFeePerCard - shippingPerCard - rawSaleNet;

  const breakEvenPsa10Price = solveBreakEvenSellingPrice(
    totalCostPerCard,
    sellFeeRate,
    sellShippingPerCard
  );

  const non10Share9 = remaining > 0 ? probPsa9 / remaining : 0.85;
  const non10Share8 = remaining > 0 ? probPsa8OrLower / remaining : 0.15;
  const non10ExpectedProfit = non10Share9 * profit9 + non10Share8 * profit8;

  let requiredPsa10Rate = null;
  if (non10ExpectedProfit >= 0 && profit10 >= 0) {
    requiredPsa10Rate = 0;
  } else if (profit10 > non10ExpectedProfit && profit10 > 0) {
    const ratio = -non10ExpectedProfit / (profit10 - non10ExpectedProfit);
    requiredPsa10Rate = Math.min(100, Math.max(0, ratio * 100));
  }

  const sensitivityRates = [40, 50, 60, 70, 80, 90];
  const sensitivityTable = sensitivityRates.map((rate) => {
    const r10 = rate / 100;
    const rNon10 = 1 - r10;
    const ev = Math.round(r10 * profit10 + rNon10 * non10ExpectedProfit);
    const totalEv = ev * cardCount;
    const roi = totalCostPerCard > 0 ? (ev / totalCostPerCard) * 100 : 0;
    return {
      psa10Rate: rate,
      expectedProfitPerCard: ev,
      expectedTotalProfit: totalEv,
      roi,
    };
  });

  let verdict = 'neutral';
  if (expectedProfitPerCard > 0 && advantageOverRawSale > 0) {
    verdict = 'submit';
  } else if (expectedProfitPerCard <= 0) {
    verdict = 'skip';
  } else {
    verdict = 'caution';
  }

  return {
    rawCardCost,
    gradingFeePerCard,
    cardCount,
    totalShippingCost,
    shippingPerCard,
    totalCostPerCard,
    totalInvestment: totalCostPerCard * cardCount,
    sellFeeRate,
    sellShippingPerCard,
    probPsa10,
    probPsa9,
    probPsa8OrLower,
    grades: {
      psa10: { price: pricePsa10, net: net10, profit: profit10, roi: roi10 },
      psa9: { price: pricePsa9, net: net9, profit: profit9, roi: roi9 },
      psa8: { price: pricePsa8OrLower, net: net8, profit: profit8, roi: roi8 },
    },
    expectedNetPerCard,
    expectedProfitPerCard,
    expectedTotalProfit,
    expectedRoi,
    advantageOverRawSale,
    breakEvenPsa10Price,
    requiredPsa10Rate,
    sensitivityTable,
    verdict,
  };
}

/**
 * 超幾何分布 P(X = 0): 総数N個中、当たりK個のくじを非復元でn回引いたときに1回も当たらない確率
 */
export function hypergeometricZeroProbability(totalN, successK, drawsN) {
  const N = Math.floor(totalN);
  const K = Math.floor(successK);
  const n = Math.floor(drawsN);

  if (N <= 0 || n <= 0 || K <= 0) return 1;
  if (K >= N) return 0;
  if (n > N - K) return 0;

  let prob = 1;
  for (let i = 0; i < n; i += 1) {
    prob *= (N - K - i) / (N - i);
  }
  return Math.max(0, Math.min(1, prob));
}

export const ORIPA_PRESETS = {
  mild: {
    label: '王道マイルド（1口1,000円 / 100口）',
    unitPrice: 1000,
    totalPacks: 100,
    drawCount: 5,
    missValue: 300,
    cashoutRate: 0.80,
    prizes: [
      { name: 'S賞（トップ当たり）', value: 25000, count: 1 },
      { name: 'A賞（大当たり）', value: 8000, count: 3 },
      { name: 'B賞（小当たり・アド）', value: 2000, count: 12 },
    ],
  },
  nibuichi: {
    label: 'ニブイチ系（1口3,000円 / 200口）',
    unitPrice: 3000,
    totalPacks: 200,
    drawCount: 3,
    missValue: 500,
    cashoutRate: 0.80,
    prizes: [
      { name: 'S賞（超高額PSA10）', value: 60000, count: 2 },
      { name: 'A賞（BOX / 人気SAR）', value: 12000, count: 8 },
      { name: 'ニブイチ還元枠', value: 3500, count: 90 },
    ],
  },
  highrisk: {
    label: '高額ハイリスク（1口10,000円 / 50口）',
    unitPrice: 10000,
    totalPacks: 50,
    drawCount: 2,
    missValue: 2000,
    cashoutRate: 0.78,
    prizes: [
      { name: 'S賞（超目玉カード）', value: 180000, count: 1 },
      { name: 'A賞（高額枠）', value: 45000, count: 3 },
      { name: 'B賞（アド確定枠）', value: 15000, count: 6 },
    ],
  },
};

/**
 * ツール3: オリパ 還元率・期待値・爆死確率シミュレーター
 */
export function calculateOripaSimulation(input) {
  const unitPrice = Math.round(clampNumber(input.unitPrice, 1));
  const totalPacks = Math.max(1, Math.round(clampNumber(input.totalPacks, 1, 1000000)));
  const drawCount = Math.max(1, Math.min(totalPacks, Math.round(clampNumber(input.drawCount, 1))));
  const missValue = Math.round(clampNumber(input.missValue, 0));
  const cashoutRate = clampNumber(input.cashoutRate ?? 1, 0.1, 1.0);

  const sanitizedPrizes = (Array.isArray(input.prizes) ? input.prizes : []).map((p, idx) => ({
    name: String(p.name || `当たり枠 ${idx + 1}`).trim(),
    value: Math.round(clampNumber(p.value, 0)),
    count: Math.max(0, Math.round(clampNumber(p.count, 0))),
  }));

  const totalPrizeCount = sanitizedPrizes.reduce((acc, p) => acc + p.count, 0);
  const missCount = totalPacks - totalPrizeCount;
  const isValid = missCount >= 0;

  if (!isValid) {
    return {
      isValid: false,
      error: `当たり本数の合計（${totalPrizeCount}口）が総口数（${totalPacks}口）を超えています。`,
      unitPrice,
      totalPacks,
      drawCount,
      totalPrizeCount,
      missCount,
    };
  }

  const prizeTotalValue = sanitizedPrizes.reduce((acc, p) => acc + p.value * p.count, 0);
  const totalPoolValue = prizeTotalValue + missValue * missCount;
  const totalCostPool = unitPrice * totalPacks;

  const evPerPack = totalPoolValue / totalPacks;
  const returnRate = (evPerPack / unitPrice) * 100;
  const expectedProfitPerPack = evPerPack - unitPrice;

  const cashoutEvPerPack = evPerPack * cashoutRate;
  const cashoutReturnRate = returnRate * cashoutRate;
  const cashoutExpectedProfitPerPack = cashoutEvPerPack - unitPrice;

  const adPrizeCount = sanitizedPrizes
    .filter((p) => p.value >= unitPrice)
    .reduce((acc, p) => acc + p.count, 0) + (missValue >= unitPrice ? missCount : 0);

  const cashoutAdCount = sanitizedPrizes
    .filter((p) => p.value * cashoutRate >= unitPrice)
    .reduce((acc, p) => acc + p.count, 0) + (missValue * cashoutRate >= unitPrice ? missCount : 0);

  const activePrizes = sanitizedPrizes.filter((p) => p.count > 0);
  const maxPrizeValue = activePrizes.length > 0 ? Math.max(...activePrizes.map((p) => p.value)) : 0;
  const topPrizeCount = activePrizes
    .filter((p) => p.value === maxPrizeValue && maxPrizeValue > missValue)
    .reduce((acc, p) => acc + p.count, 0);

  const probAtLeastOneAd = (1 - hypergeometricZeroProbability(totalPacks, adPrizeCount, drawCount)) * 100;
  const probAtLeastOneCashoutAd = (1 - hypergeometricZeroProbability(totalPacks, cashoutAdCount, drawCount)) * 100;
  const probAllMiss = hypergeometricZeroProbability(totalPacks, totalPrizeCount, drawCount) * 100;
  const probTopPrize = (1 - hypergeometricZeroProbability(totalPacks, topPrizeCount, drawCount)) * 100;

  const candidateDraws = Array.from(
    new Set([1, 3, 5, 10, 20, drawCount].filter((n) => n >= 1 && n <= totalPacks))
  ).sort((a, b) => a - b);

  const drawTable = candidateDraws.map((n) => ({
    draws: n,
    totalSpend: n * unitPrice,
    expectedReturn: Math.round(n * evPerPack),
    expectedCashout: Math.round(n * cashoutEvPerPack),
    probAtLeastOneAd: (1 - hypergeometricZeroProbability(totalPacks, adPrizeCount, n)) * 100,
    probAllMiss: hypergeometricZeroProbability(totalPacks, totalPrizeCount, n) * 100,
    probTopPrize: (1 - hypergeometricZeroProbability(totalPacks, topPrizeCount, n)) * 100,
    isCurrent: n === drawCount,
  }));

  let grade = 'C';
  let gradeLabel = 'ハイリスク・趣味向け';
  if (returnRate >= 98) {
    grade = 'S';
    gradeLabel = '超優良還元（アド狙い圏内）';
  } else if (returnRate >= 85) {
    grade = 'A';
    gradeLabel = '良心的な還元率';
  } else if (returnRate >= 70) {
    grade = 'B';
    gradeLabel = '標準的なオリパ水準';
  }

  return {
    isValid: true,
    unitPrice,
    totalPacks,
    drawCount,
    totalSpend: unitPrice * drawCount,
    missValue,
    missCount,
    cashoutRate,
    prizes: sanitizedPrizes,
    totalPrizeCount,
    totalPoolValue,
    totalCostPool,
    evPerPack,
    returnRate,
    expectedProfitPerPack,
    expectedTotalProfit: Math.round(expectedProfitPerPack * drawCount),
    cashoutEvPerPack,
    cashoutReturnRate,
    cashoutExpectedProfitPerPack,
    cashoutExpectedTotalProfit: Math.round(cashoutExpectedProfitPerPack * drawCount),
    adPrizeCount,
    adRatePerPack: (adPrizeCount / totalPacks) * 100,
    topPrizeCount,
    maxPrizeValue,
    probAtLeastOneAd,
    probAtLeastOneCashoutAd,
    probAllMiss,
    probTopPrize,
    drawTable,
    grade,
    gradeLabel,
  };
}

/**
 * オリパ運試しガチャ（非復元サンプリング）
 */
export function simulateOripaDraws(simResult, count, rng = Math.random) {
  if (!simResult.isValid) return [];
  const draws = Math.min(count, simResult.totalPacks);

  const buckets = [
    ...simResult.prizes
      .filter((p) => p.count > 0)
      .map((p) => ({ name: p.name, value: p.value, remaining: p.count, isMiss: false })),
  ];
  if (simResult.missCount > 0) {
    buckets.push({
      name: 'ハズレ（最低保証）',
      value: simResult.missValue,
      remaining: simResult.missCount,
      isMiss: true,
    });
  }

  let remainingTotal = simResult.totalPacks;
  const results = [];

  for (let i = 0; i < draws; i += 1) {
    let pick = Math.floor(rng() * remainingTotal);
    let chosen = buckets[buckets.length - 1];
    for (const bucket of buckets) {
      if (bucket.remaining <= 0) continue;
      if (pick < bucket.remaining) {
        chosen = bucket;
        break;
      }
      pick -= bucket.remaining;
    }
    chosen.remaining -= 1;
    remainingTotal -= 1;
    results.push({
      drawNumber: i + 1,
      name: chosen.name,
      value: chosen.value,
      isMiss: chosen.isMiss,
      isAd: chosen.value >= simResult.unitPrice,
      isTop: !chosen.isMiss && chosen.value === simResult.maxPrizeValue,
      net: chosen.value - simResult.unitPrice,
    });
  }

  return results;
}

export const PORTFOLIO_CATEGORIES = {
  box: { label: '未開封BOX', defaultShipping: 520 },
  psa: { label: 'PSA鑑定品', defaultShipping: 210 },
  single: { label: 'シングルカード', defaultShipping: 180 },
  other: { label: 'その他グッズ', defaultShipping: 520 },
};

/**
 * ツール4: ポートフォリオ資産・含み損益・手取り換算計算
 */
export function calculatePortfolioSummary(items) {
  const safeItems = Array.isArray(items) ? items : [];
  let totalCost = 0;
  let totalMarketValue = 0;
  let totalEstimatedFleaNet = 0;
  let totalQuantity = 0;

  const categoryTotals = {};
  for (const key of Object.keys(PORTFOLIO_CATEGORIES)) {
    categoryTotals[key] = { key, label: PORTFOLIO_CATEGORIES[key].label, marketValue: 0, cost: 0, count: 0 };
  }

  const enrichedItems = safeItems.map((item) => {
    const qty = Math.max(1, Math.round(clampNumber(item.quantity, 1, 9999)));
    const buyPrice = Math.round(clampNumber(item.buyPrice, 0));
    const currentPrice = Math.round(clampNumber(item.currentPrice, 0));
    const category = PORTFOLIO_CATEGORIES[item.category] ? item.category : 'box';

    const costBasis = qty * buyPrice;
    const marketValue = qty * currentPrice;
    const pnl = marketValue - costBasis;
    const roi = costBasis > 0 ? (pnl / costBasis) * 100 : 0;

    const shippingPerUnit = PORTFOLIO_CATEGORIES[category].defaultShipping;
    const estimatedFleaNet = Math.max(
      0,
      marketValue - Math.floor(marketValue * 0.10) - shippingPerUnit * qty
    );

    totalCost += costBasis;
    totalMarketValue += marketValue;
    totalEstimatedFleaNet += estimatedFleaNet;
    totalQuantity += qty;

    categoryTotals[category].marketValue += marketValue;
    categoryTotals[category].cost += costBasis;
    categoryTotals[category].count += qty;

    return {
      ...item,
      category,
      quantity: qty,
      buyPrice,
      currentPrice,
      costBasis,
      marketValue,
      pnl,
      roi,
      estimatedFleaNet,
    };
  });

  const totalPnl = totalMarketValue - totalCost;
  const totalRoi = totalCost > 0 ? (totalPnl / totalCost) * 100 : 0;
  const netPnlAfterFlea = totalEstimatedFleaNet - totalCost;

  const categoryBreakdown = Object.values(categoryTotals)
    .filter((c) => c.count > 0)
    .map((c) => ({
      ...c,
      share: totalMarketValue > 0 ? (c.marketValue / totalMarketValue) * 100 : 0,
    }))
    .sort((a, b) => b.marketValue - a.marketValue);

  return {
    items: enrichedItems,
    itemCount: enrichedItems.length,
    totalQuantity,
    totalCost,
    totalMarketValue,
    totalPnl,
    totalRoi,
    totalEstimatedFleaNet,
    netPnlAfterFlea,
    categoryBreakdown,
  };
}

/**
 * ポートフォリオCSV出力（Excel文字化け対策UTF-8 BOM対応用データ生成）
 */
export function portfolioToCsv(items) {
  const headers = ['商品名', 'カテゴリ', '状態', '数量', '購入単価', '現在相場', 'メモ'];
  const escapeCell = (val) => {
    const str = String(val ?? '');
    if (/[",\n\r]/.test(str)) {
      return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
  };
  const rows = (items || []).map((item) => [
    item.name || '',
    item.category || 'box',
    item.condition || 'シュリンク有',
    item.quantity ?? 1,
    item.buyPrice ?? 0,
    item.currentPrice ?? 0,
    item.note || '',
  ].map(escapeCell).join(','));

  return [headers.join(','), ...rows].join('\n');
}

/**
 * ポートフォリオCSV読み込み（引用符・カンマ入り値対応）
 */
export function parsePortfolioCsv(csvText) {
  const cleaned = String(csvText || '').replace(/^\uFEFF/, '').trim();
  if (!cleaned) return [];

  const rows = [];
  let row = [];
  let cell = '';
  let inQuotes = false;

  for (let i = 0; i < cleaned.length; i += 1) {
    const ch = cleaned[i];
    const next = cleaned[i + 1];

    if (inQuotes) {
      if (ch === '"' && next === '"') {
        cell += '"';
        i += 1;
      } else if (ch === '"') {
        inQuotes = false;
      } else {
        cell += ch;
      }
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === ',') {
      row.push(cell);
      cell = '';
    } else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && next === '\n') i += 1;
      row.push(cell);
      if (row.some((c) => c.trim() !== '')) rows.push(row);
      row = [];
      cell = '';
    } else {
      cell += ch;
    }
  }
  row.push(cell);
  if (row.some((c) => c.trim() !== '')) rows.push(row);

  if (rows.length <= 1) return [];

  const categoryAliases = {
    box: 'box',
    '未開封BOX': 'box',
    psa: 'psa',
    'PSA鑑定品': 'psa',
    single: 'single',
    'シングルカード': 'single',
    other: 'other',
    'その他グッズ': 'other',
  };

  return rows.slice(1).map((cols, idx) => ({
    id: `imp_${Date.now()}_${idx}`,
    name: String(cols[0] || '').trim() || `アイテム ${idx + 1}`,
    category: categoryAliases[String(cols[1] || '').trim()] || 'box',
    condition: String(cols[2] || '').trim() || 'シュリンク有',
    quantity: Math.max(1, Math.round(clampNumber(cols[3], 1, 9999))),
    buyPrice: Math.round(clampNumber(cols[4], 0)),
    currentPrice: Math.round(clampNumber(cols[5], 0)),
    note: String(cols[6] || '').trim(),
  }));
}
