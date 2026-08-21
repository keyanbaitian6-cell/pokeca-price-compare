const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const test = require('node:test');

const { _test } = require('../api/update');

test('合言葉はSHA-256ハッシュと定数時間比較される', () => {
  const hash = crypto.createHash('sha256').update('正しい合言葉').digest('hex');
  assert.equal(_test.verifyPassphrase('正しい合言葉', hash), true);
  assert.equal(_test.verifyPassphrase('違う合言葉', hash), false);
  assert.equal(_test.verifyPassphrase('', hash), false);
});

test('同一オリジンのみ許可する', () => {
  assert.equal(
    _test.isSameOrigin({
      headers: { origin: 'https://example.vercel.app', host: 'example.vercel.app' },
    }),
    true,
  );
  assert.equal(
    _test.isSameOrigin({
      headers: { origin: 'https://evil.example', host: 'example.vercel.app' },
    }),
    false,
  );
});

test('直近5分以内の実行は待機時間を返す', async (context) => {
  const originalFetch = global.fetch;
  context.after(() => {
    global.fetch = originalFetch;
  });
  global.fetch = async () => ({
    ok: true,
    json: async () => ({
      workflow_runs: [{ status: 'completed', created_at: '2026-08-18T09:00:00Z' }],
    }),
  });

  const now = Date.parse('2026-08-18T09:02:10Z');
  assert.equal(await _test.getCooldownMinutes('dummy-token', now), 3);
});

test('5分を過ぎた完了済み実行は再実行できる', async (context) => {
  const originalFetch = global.fetch;
  context.after(() => {
    global.fetch = originalFetch;
  });
  global.fetch = async () => ({
    ok: true,
    json: async () => ({
      workflow_runs: [{ status: 'completed', created_at: '2026-08-18T09:00:00Z' }],
    }),
  });

  const now = Date.parse('2026-08-18T09:06:00Z');
  assert.equal(await _test.getCooldownMinutes('dummy-token', now), 0);
});

test('買取マッチョ込み更新は日本時間15時から19時未満だけ許可する', () => {
  assert.equal(_test.isMachoPriceWindow(new Date('2026-08-21T05:59:59Z')), false);
  assert.equal(_test.isMachoPriceWindow(new Date('2026-08-21T06:00:00Z')), true);
  assert.equal(_test.isMachoPriceWindow(new Date('2026-08-21T09:59:59Z')), true);
  assert.equal(_test.isMachoPriceWindow(new Date('2026-08-21T10:00:00Z')), false);
});

test('更新方法ごとに実行する取得元を固定する', () => {
  assert.equal(_test.requestedSources('standard'), 'collect,runto,somurie');
  assert.equal(_test.requestedSources('with_macho'), 'collect,runto,somurie,macho');
  assert.equal(_test.requestedSources('unknown'), null);
});
