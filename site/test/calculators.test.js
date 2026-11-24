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
} from '../js/calculators.js';

test('solveBreakEvenSellingPrice accounts for floored platform fees accurately', () => {
  // 目標手取り 10,000円、手数料10%、送料+梱包 640円
  const price = solveBreakEvenSellingPrice(10000, 0.10, 640);
  const net = price - Math.floor(price * 0.10) - 640;
  const prevNet = (price - 1) - Math.floor((price - 1) * 0.10) - 640;

  assert.ok(net >= 10000, `expected net ${net} >= 10000`);
  assert.ok(prevNet < 10000, `expected prevNet ${prevNet} < 10000`);
});

test('calculateSellComparison identifies flea vs buyback winner and cross-platform table', () => {
  const res = calculateSellComparison({
    fleaPrice: 12000,
    platformFeeRate: 0.10,
    shippingCost: 520,
    packingCost: 120,
    buybackPrice: 10500,
    buybackCost: 0,
    purchaseCost: 5400,
    effortCost: 0,
  });

  // 12000 - 1200 - 520 - 120 = 10160 < 10500 -> buyback wins by 340
  assert.equal(res.platformFee, 1200);
  assert.equal(res.fleaNet, 10160);
  assert.equal(res.buybackNet, 10500);
  assert.equal(res.rawDiff, -340);
  assert.equal(res.winner, 'buyback');
  assert.equal(res.buybackProfit, 5100);
  assert.equal(res.fleaProfit, 4760);

  // Yahoo!フリマ (5% = 600円 -> 12000 - 600 - 640 = 10760) beats buyback (10500)!
  assert.equal(res.platformComparisons[0].id, 'yahoo_flea');
  assert.equal(res.platformComparisons[0].net, 10760);
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

  // fleaNet = 13000 - 1300 - 640 = 11060 -> rawDiff = +260, but minus 500 effort => -240 (buyback)
  assert.equal(res.rawDiff, 260);
  assert.equal(res.effectiveDiff, -240);
  assert.equal(res.winner, 'buyback');
  assert.equal(res.isCloseCall, true);
});

test('calculatePsaSimulation computes per-card costs, EV, and required PSA10 rate', () => {
  const res = calculatePsaSimulation({
    rawCardCost: 10000,
    gradingFeePerCard: 3300,
    cardCount: 5,
    totalShippingCost: 2000,
    sellFeeRate: 0.10,
    sellShippingPerCard: 210,
    pricePsa10: 25000,
    pricePsa9: 11000,
    pricePsa8OrLower: 7000,
    probPsa10: 70,
  });

  // shippingPerCard = 400, totalCost = 13700
  assert.equal(res.shippingPerCard, 400);
  assert.equal(res.totalCostPerCard, 13700);
  // net10 = 25000 - 2500 - 210 = 22290 -> profit10 = +8590
  assert.equal(res.grades.psa10.profit, 8590);
  // net9 = 11000 - 1100 - 210 = 9690 -> profit9 = -4010
  assert.equal(res.grades.psa9.profit, -4010);
  assert.ok(res.expectedProfitPerCard > 0);
  assert.equal(res.verdict, 'submit');
  assert.ok(res.requiredPsa10Rate > 25 && res.requiredPsa10Rate < 50);
  assert.equal(res.sensitivityTable.length, 6);
});

test('hypergeometricZeroProbability computes exact without-replacement probabilities', () => {
  // 10口中2口当たり、2口引いたときの全外れ確率 = (8/10) * (7/9) = 56/90
  const p = hypergeometricZeroProbability(10, 2, 2);
  assert.ok(Math.abs(p - 56 / 90) < 1e-12);

  // 総口数10・当たり3口で8口引けば必ず1回は当たる -> 全外れ確率0
  assert.equal(hypergeometricZeroProbability(10, 3, 8), 0);

  // 大規模口数でもNaN・オーバーフローしない
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
  // S: 25000*1 + A: 8000*3 + B: 2000*12 + miss: 300*84 = 25000+24000+24000+25200 = 98200
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
  const topHits = draws.filter((d) => d.isTop);
  assert.equal(topHits.length, 1);
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
  assert.equal(summary.categoryBreakdown.length, 2);

  const csv = portfolioToCsv(items);
  const parsed = parsePortfolioCsv(`\uFEFF${csv}`);
  assert.equal(parsed.length, 2);
  assert.equal(parsed[0].name, 'ポケモンカード151, 初版');
  assert.equal(parsed[0].note, 'ポケセン産 "保管用"');
  assert.equal(parsed[0].quantity, 2);
  assert.equal(parsed[1].category, 'psa');
});
