const crypto = require('node:crypto');

const GITHUB_OWNER = 'keyanbaitian6-cell';
const GITHUB_REPO = 'pokeca-price-compare';
const WORKFLOW_FILE = 'manual-update.yml';
const WORKFLOW_REF = 'main';
const MIN_INTERVAL_MS = 5 * 60 * 1000;
const GITHUB_API_VERSION = '2022-11-28';

function sendJson(response, status, body) {
  response.setHeader('Cache-Control', 'no-store');
  response.setHeader('Content-Type', 'application/json; charset=utf-8');
  response.status(status).json(body);
}

function isSameOrigin(request) {
  const origin = request.headers.origin;
  const host = request.headers['x-forwarded-host'] || request.headers.host;
  return Boolean(origin && host && origin === `https://${host}`);
}

function verifyPassphrase(passphrase, expectedHash) {
  if (typeof passphrase !== 'string' || passphrase.length === 0 || passphrase.length > 128) {
    return false;
  }
  if (!/^[a-f0-9]{64}$/i.test(expectedHash || '')) {
    throw new Error('UPDATE_PASSWORD_HASH is not configured');
  }

  const actual = crypto.createHash('sha256').update(passphrase, 'utf8').digest();
  const expected = Buffer.from(expectedHash, 'hex');
  return actual.length === expected.length && crypto.timingSafeEqual(actual, expected);
}

function githubHeaders(token) {
  return {
    Accept: 'application/vnd.github+json',
    Authorization: `Bearer ${token}`,
    'X-GitHub-Api-Version': GITHUB_API_VERSION,
    'User-Agent': 'pokeca-price-manual-updater',
  };
}

async function githubRequest(path, options, token) {
  return fetch(`https://api.github.com${path}`, {
    ...options,
    headers: {
      ...githubHeaders(token),
      ...(options.headers || {}),
    },
  });
}

async function getCooldownMinutes(token, now = Date.now()) {
  const path =
    `/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/workflows/` +
    `${WORKFLOW_FILE}/runs?per_page=1`;
  const response = await githubRequest(path, { method: 'GET' }, token);
  if (!response.ok) {
    throw new Error(`GitHub workflow history returned HTTP ${response.status}`);
  }

  const data = await response.json();
  const latest = Array.isArray(data.workflow_runs) ? data.workflow_runs[0] : null;
  if (!latest) {
    return 0;
  }

  const createdAt = Date.parse(latest.created_at);
  const remainingMs = MIN_INTERVAL_MS - (now - createdAt);
  if (latest.status === 'queued' || latest.status === 'in_progress' || remainingMs > 0) {
    return Math.max(1, Math.ceil(Math.max(remainingMs, 60_000) / 60_000));
  }
  return 0;
}

async function dispatchWorkflow(token) {
  const path =
    `/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/workflows/` +
    `${WORKFLOW_FILE}/dispatches`;
  const response = await githubRequest(
    path,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ref: WORKFLOW_REF }),
    },
    token,
  );
  if (response.status !== 204) {
    throw new Error(`GitHub workflow dispatch returned HTTP ${response.status}`);
  }
}

async function handler(request, response) {
  if (request.method !== 'POST') {
    response.setHeader('Allow', 'POST');
    return sendJson(response, 405, { ok: false, message: 'この操作には対応していません。' });
  }
  if (!isSameOrigin(request)) {
    return sendJson(response, 403, { ok: false, message: 'このページから操作してください。' });
  }

  const token = process.env.GITHUB_TOKEN;
  const expectedHash = process.env.UPDATE_PASSWORD_HASH;
  if (!token || !expectedHash) {
    console.error('Required Vercel environment variables are missing');
    return sendJson(response, 503, {
      ok: false,
      message: '更新機能の準備が完了していません。管理者に連絡してください。',
    });
  }

  let passwordMatches = false;
  try {
    passwordMatches = verifyPassphrase(request.body?.passphrase, expectedHash);
  } catch (error) {
    console.error(error.message);
    return sendJson(response, 503, {
      ok: false,
      message: '更新機能の準備が完了していません。管理者に連絡してください。',
    });
  }
  if (!passwordMatches) {
    return sendJson(response, 401, { ok: false, message: '合言葉が違います。' });
  }

  try {
    const cooldownMinutes = await getCooldownMinutes(token);
    if (cooldownMinutes > 0) {
      return sendJson(response, 429, {
        ok: false,
        message: `更新中または連続実行防止中です。約${cooldownMinutes}分後にお試しください。`,
      });
    }

    await dispatchWorkflow(token);
    return sendJson(response, 202, {
      ok: true,
      message: '更新を受け付けました。通常は数分で価格表へ反映されます。',
    });
  } catch (error) {
    console.error(error.message);
    return sendJson(response, 502, {
      ok: false,
      message: '更新を開始できませんでした。時間を置いて再度お試しください。',
    });
  }
}

module.exports = handler;
module.exports._test = {
  dispatchWorkflow,
  getCooldownMinutes,
  isSameOrigin,
  verifyPassphrase,
};
