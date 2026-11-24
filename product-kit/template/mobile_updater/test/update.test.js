const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const test = require('node:test');

const { _test } = require('../api/update');

const SAMPLE_HASH = crypto.createHash('sha256').update('my-secret-passphrase').digest('hex');

test('合言葉はSHA-256ハッシュと定数時間比較される', () => {
  assert.equal(_test.verifyPassphrase('my-secret-passphrase', SAMPLE_HASH), true);
  assert.equal(_test.verifyPassphrase('wrong-passphrase', SAMPLE_HASH), false);
  assert.equal(_test.verifyPassphrase('', SAMPLE_HASH), false);
});

test('同一オリジンのみ許可する', () => {
  assert.equal(
    _test.isSameOrigin({
      headers: { origin: 'https://my-updater.vercel.app', host: 'my-updater.vercel.app' },
    }),
    true,
  );
  assert.equal(
    _test.isSameOrigin({
      headers: { origin: 'https://evil.example', host: 'my-updater.vercel.app' },
    }),
    false,
  );
});

test('環境変数から汎用設定を読み込み、クールダウンは最低5分を下回らない', () => {
  const cfg = _test.readRuntimeConfig({
    GITHUB_OWNER: 'example-user',
    GITHUB_REPO: 'my-price-monitor',
    GITHUB_TOKEN: 'dummy-token',
    UPDATE_PASSWORD_HASH: SAMPLE_HASH,
    MIN_INTERVAL_MINUTES: '1',
  });
  assert.equal(cfg.owner, 'example-user');
  assert.equal(cfg.repo, 'my-price-monitor');
  assert.equal(cfg.workflowFile, 'update-prices.yml');
  assert.equal(cfg.minIntervalMs, 5 * 60 * 1000);
});

test('直近5分以内の実行は待機時間を返す', async (context) => {
  const originalFetch = global.fetch;
  context.after(() => {
    global.fetch = originalFetch;
  });
  global.fetch = async () => ({
    ok: true,
    json: async () => ({
      workflow_runs: [{ status: 'completed', created_at: '2026-10-01T09:00:00Z' }],
    }),
  });

  const cfg = {
    owner: 'example-user',
    repo: 'my-price-monitor',
    workflowFile: 'update-prices.yml',
    token: 'dummy-token',
    minIntervalMs: 5 * 60 * 1000,
  };
  const now = Date.parse('2026-10-01T09:02:10Z');
  assert.equal(await _test.getCooldownMinutes(cfg, now), 3);
});

test('5分経過後の完了済み実行は再実行できる', async (context) => {
  const originalFetch = global.fetch;
  context.after(() => {
    global.fetch = originalFetch;
  });
  global.fetch = async () => ({
    ok: true,
    json: async () => ({
      workflow_runs: [{ status: 'completed', created_at: '2026-10-01T09:00:00Z' }],
    }),
  });

  const cfg = {
    owner: 'example-user',
    repo: 'my-price-monitor',
    workflowFile: 'update-prices.yml',
    token: 'dummy-token',
    minIntervalMs: 5 * 60 * 1000,
  };
  const now = Date.parse('2026-10-01T09:06:00Z');
  assert.equal(await _test.getCooldownMinutes(cfg, now), 0);
});
