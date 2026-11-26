const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const test = require('node:test');

const { _test } = require('../cloudflare_worker');

const SAMPLE_HASH = crypto.createHash('sha256').update('cf-passphrase-2026').digest('hex');

test('Cloudflare Worker: Web Crypto SHA-256 定数時間比較が動作する', async () => {
  assert.equal(await _test.verifyPassphrase('cf-passphrase-2026', SAMPLE_HASH), true);
  assert.equal(await _test.verifyPassphrase('wrong', SAMPLE_HASH), false);
  assert.equal(await _test.verifyPassphrase('', SAMPLE_HASH), false);
});

test('Cloudflare Worker: クールダウン下限は5分未満にならない', () => {
  const cfg = _test.readRuntimeConfig({
    GITHUB_OWNER: 'demo-owner',
    GITHUB_REPO: 'demo-repo',
    GITHUB_TOKEN: 'dummy',
    UPDATE_PASSWORD_HASH: SAMPLE_HASH,
    MIN_INTERVAL_MINUTES: '2',
  });
  assert.equal(cfg.minIntervalMs, 5 * 60 * 1000);
});

test('Cloudflare Worker: 同一オリジン＋正しい合言葉でワークフローを起動できる', async () => {
  let dispatched = false;
  const fakeFetch = async (url, opts) => {
    if (opts.method === 'GET') {
      return {
        ok: true,
        json: async () => ({
          workflow_runs: [{ status: 'completed', created_at: '2026-01-01T00:00:00Z' }],
        }),
      };
    }
    dispatched = true;
    assert.ok(url.includes('/dispatches'));
    return { status: 204 };
  };

  const req = new Request('https://my-updater.workers.dev/api/update', {
    method: 'POST',
    headers: {
      origin: 'https://my-updater.workers.dev',
      'content-type': 'application/json',
    },
    body: JSON.stringify({ passphrase: 'cf-passphrase-2026' }),
  });

  const env = {
    GITHUB_OWNER: 'demo-owner',
    GITHUB_REPO: 'demo-repo',
    GITHUB_TOKEN: 'dummy-token',
    UPDATE_PASSWORD_HASH: SAMPLE_HASH,
  };

  const resp = await _test.handleApiUpdate(req, env, fakeFetch);
  assert.equal(resp.status, 202);
  assert.equal(dispatched, true);
  const payload = await resp.json();
  assert.equal(payload.ok, true);
});

test('Cloudflare Worker: 異なるオリジンからのリクエストを403で拒否する', async () => {
  const req = new Request('https://my-updater.workers.dev/api/update', {
    method: 'POST',
    headers: {
      origin: 'https://evil.example',
      'content-type': 'application/json',
    },
    body: JSON.stringify({ passphrase: 'cf-passphrase-2026' }),
  });

  const resp = await _test.handleApiUpdate(req, {}, async () => ({ ok: true }));
  assert.equal(resp.status, 403);
});
