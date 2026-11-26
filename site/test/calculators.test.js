import test from 'node:test';
import assert from 'node:assert/strict';
import {
  solveBreakEvenSellingPrice,
  calculateSellComparison,
  calculatePsaSimulation,
  hypergeometricZeroProbability,
  calculateOripaSimulation,
  simulateOripaDraws,
  calculatePortfolioSummary,
  portfolioToCsv,
  parsePortfolioCsv,
  ORIPA_PRESETS,
  PSA_PLAN_PRESETS,
} from '../js/calculators.js';

test('solveBreakEvenSellingPrice accounts for floored platform fees accurately', () => {
  const price = solveBreakEvenSellingPrice(10000, 0.10, 640);
  const net = price - Math.floor(price * 0.10) - 640;
  const prevNet = (price - 1) - Math.floor((price - 1) * 0.10) - 640;

  assert.ok(net >= 10000, `expected net ${net} >= 10000`);
  assert.ok(prevNet < 10000, `expected prevNet ${prevNet} < 10000`);
});

test('calculateSellComparison identifies flea vs buyback winner, cross-platform table, and withdrawal fee', () => {
  const res = calculateSellComparison({
    fleaPrice: 12000,
    platformFeeRate: 0.10,
    shippingCost: 520,
    packingCost: 120,
    buybackPrice: 10500,
    buybackCost: 0,
    purchaseCost: 5400,
    effortCost: 0,
    includeWithdrawalFee: false,
  });

  // 12000 - 1200 - 520 - 120 = 10160 < 10500 -> buyback wins by 340
  assert.equal(res.platformFee, 1200);
  assert.equal(res.fleaNet, 10160);
  assert.equal(res.buybackNet, 10500);
  assert.equal(res.rawDiff, -340);
  assert.equal(res.winner, 'buyback');
  assert.equal(res.buybackProfit, 5100);
  assert.equal(res.fleaProfit, 4760);

  // Yahoo!フリマ (5% = 600円 -> 10760) beats buyback (10500)
  assert.equal(res.platformComparisons[0].id, 'yahoo_flea');
  assert.equal(res.platformComparisons[0].net, 10760);
  assert.equal(res.platformComparisons.length, 7); // 6 flea + buyback

  // With withdrawal fee enabled (Mercari 200円 -> 9960)
  const withWithdrawal = calculateSellComparison({
    fleaPrice: 12000,
    platformFeeRate: 0.10,
    shippingCost: 520,
    packingCost: 120,
    buybackPrice: 10500,
    includeWithdrawalFee: true,
    withdrawalFee: 200,
  });
  assert.equal(withWithdrawal.withdrawalFee, 200);
  assert.equal(withWithdrawal.fleaNet, 9960);
});

test('calculateSellComparison produces accurate price-drop negotiation table', () => {
  const res = calculateSellComparison({
    fleaPrice: 14000,
    platformFeeRate: 0.10,
    shippingCost: 520,
    packingCost: 120,
    buybackPrice: 11200,
  });

  // 14,000 -> net 11,960 (beats 11,200); 13,000 (-1000) -> net 11,060 (loses to 11,200)
  assert.ok(res.priceDropTable.length >= 4);
  assert.equal(res.priceDropTable[0].drop, 0);
  assert.equal(res.priceDropTable[0].beatsBuyback, true);
  const drop1000 = res.priceDropTable.find((r) => r.drop === 1000);
  assert.ok(drop1000);
  assert.equal(drop1000.net, 11060);
  assert.equal(drop1000.beatsBuyback, false);
});

test('calculateSellComparison respects effortCost in effective winner calculation', () => {
  const res = calculateSellComparison({
    fleaPrice: 13000,
    platformFeeRate: 0.10,
    shippingCost: 520,
    packingCost: 120,
    buybackPrice: 10800,
    buybackCost: 0,
    effortCost: 500,
  });

  assert.equal(res.rawDiff, 260);
  assert.equal(res.effectiveDiff, -240);
  assert.equal(res.winner, 'buyback');
  assert.equal(res.isCloseCall, true);
});

test('calculatePsaSimulation uses 2026 PSA Japan plans and computes EV + required PSA10 rate', () => {
  assert.equal(PSA_PLAN_PRESETS[0].fee, 5980); // 2026 PSA Japan Value

  const res = calculatePsaSimulation({
    rawCardCost: 12000,
    gradingFeePerCard: 5980,
    cardCount: 5,
    totalShippingCost: 2500,
    sellFeeRate: 0.10,
    sellShippingPerCard: 210,
    pricePsa10: 34000,
    pricePsa9: 13000,
    pricePsa8OrLower: 8000,
    probPsa10: 70,
  });

  // shippingPerCard = 500, totalCost = 18480
  assert.equal(res.shippingPerCard, 500);
  assert.equal(res.totalCostPerCard, 18480);
  // net10 = 34000 - 3400 - 210 = 30390 -> profit10 = +11910
  assert.equal(res.grades.psa10.profit, 11910);
  assert.ok(res.expectedProfitPerCard > 0);
  assert.equal(res.verdict, 'submit');
  assert.ok(res.requiredPsa10Rate > 30 && res.requiredPsa10Rate < 60);
  assert.equal(res.sensitivityTable.length, 6);
});

test('hypergeometricZeroProbability computes exact without-replacement probabilities', () => {
  const p = hypergeometricZeroProbability(10, 2, 2);
  assert.ok(Math.abs(p - 56 / 90) < 1e-12);
  assert.equal(hypergeometricZeroProbability(10, 3, 8), 0);

  const large = hypergeometricZeroProbability(100000, 1000, 10);
  assert.ok(Number.isFinite(large) && large > 0.9 && large < 0.91);
});

test('calculateOripaSimulation validates prize overflow and computes EV + cashout EV', () => {
  const invalid = calculateOripaSimulation({
    unitPrice: 1000,
    totalPacks: 10,
    drawCount: 1,
    missValue: 200,
    prizes: [{ name: 'S賞', value: 5000, count: 12 }],
  });
  assert.equal(invalid.isValid, false);

  const valid = calculateOripaSimulation(ORIPA_PRESETS.mild);
  assert.equal(valid.isValid, true);
  assert.equal(valid.missCount, 84);
  assert.equal(valid.totalPoolValue, 98200);
  assert.ok(Math.abs(valid.returnRate - 98.2) < 1e-9);
  assert.ok(Math.abs(valid.cashoutReturnRate - 98.2 * 0.8) < 1e-9);
  assert.equal(valid.adPrizeCount, 16);
  assert.equal(valid.grade, 'S');
});

test('simulateOripaDraws performs valid without-replacement sampling', () => {
  const sim = calculateOripaSimulation({
    unitPrice: 1000,
    totalPacks: 5,
    drawCount: 5,
    missValue: 100,
    prizes: [{ name: 'S賞', value: 5000, count: 1 }],
  });
  const draws = simulateOripaDraws(sim, 5, () => 0.42);
  assert.equal(draws.length, 5);
  assert.equal(draws.filter((d) => d.isTop).length, 1);
});

test('portfolio summary and CSV round-trip preserve Japanese values and quotes', () => {
  const items = [
    {
      id: '1',
      name: 'ポケモンカード151, 初版',
      category: 'box',
      condition: 'シュリンク有',
      quantity: 2,
      buyPrice: 5800,
      currentPrice: 18500,
      note: 'ポケセン産 "保管用"',
    },
    {
      id: '2',
      name: 'ピカチュウex SAR PSA10',
      category: 'psa',
      condition: 'PSA10',
      quantity: 1,
      buyPrice: 40000,
      currentPrice: 52000,
      note: '',
    },
  ];

  const summary = calculatePortfolioSummary(items);
  assert.equal(summary.totalQuantity, 3);
  assert.equal(summary.totalCost, 51600);
  assert.equal(summary.totalMarketValue, 89000);
  assert.equal(summary.totalPnl, 37400);

  const csv = portfolioToCsv(items);
  const parsed = parsePortfolioCsv(`\uFEFF${csv}`);
  assert.equal(parsed.length, 2);
  assert.equal(parsed[0].name, 'ポケモンカード151, 初版');
  assert.equal(parsed[0].note, 'ポケセン産 "保管用"');
});
