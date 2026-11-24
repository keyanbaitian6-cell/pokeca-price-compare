const crypto = require('node:crypto');

const DEFAULT_WORKFLOW_FILE = 'update-prices.yml';
const DEFAULT_WORKFLOW_REF = 'main';
const MIN_SAFE_INTERVAL_MINUTES = 5;
const GITHUB_API_VERSION = '2022-11-28';
const SAFE_SEGMENT_RE = /^[a-zA-Z0-9._-]{1,100}$/;

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

function readRuntimeConfig(env = process.env) {
  const owner = (env.GITHUB_OWNER || '').trim();
  const repo = (env.GITHUB_REPO || '').trim();
  const workflowFile = (env.WORKFLOW_FILE || DEFAULT_WORKFLOW_FILE).trim();
  const workflowRef = (env.WORKFLOW_REF || DEFAULT_WORKFLOW_REF).trim();
  const token = (env.GITHUB_TOKEN || '').trim();
  const expectedHash = (env.UPDATE_PASSWORD_HASH || '').trim();

  const rawMinutes = Number(env.MIN_INTERVAL_MINUTES || MIN_SAFE_INTERVAL_MINUTES);
  const minIntervalMinutes = Number.isFinite(rawMinutes)
    ? Math.max(MIN_SAFE_INTERVAL_MINUTES, Math.floor(rawMinutes))
    : MIN_SAFE_INTERVAL_MINUTES;

  if (!owner || !repo || !token || !expectedHash) {
    return null;
  }
  if (!SAFE_SEGMENT_RE.test(owner) || !SAFE_SEGMENT_RE.test(repo) || !SAFE_SEGMENT_RE.test(workflowFile)) {
    throw new Error('Invalid GitHub repository or workflow configuration');
  }
  return {
    owner,
    repo,
    workflowFile,
    workflowRef,
    token,
    expectedHash,
    minIntervalMs: minIntervalMinutes * 60 * 1000,
  };
}

function verifyPassphrase(passphrase, expectedHash) {
  if (typeof passphrase !== 'string' || passphrase.length === 0 || passphrase.length > 128) {
    return false;
  }
  if (!/^[a-f0-9]{64}$/i.test(expectedHash || '')) {
    throw new Error('UPDATE_PASSWORD_HASH is not a valid 64-char SHA-256 hex digest');
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
    'User-Agent': 'price-monitor-kit-mobile-updater',
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

async function getCooldownMinutes(config, now = Date.now()) {
  const path =
    `/repos/${config.owner}/${config.repo}/actions/workflows/` +
    `${config.workflowFile}/runs?per_page=1`;
  const response = await githubRequest(path, { method: 'GET' }, config.token);
  if (!response.ok) {
    throw new Error(`GitHub workflow history returned HTTP ${response.status}`);
  }

  const data = await response.json();
  const latest = Array.isArray(data.workflow_runs) ? data.workflow_runs[0] : null;
  if (!latest) {
    return 0;
  }

  const createdAt = Date.parse(latest.created_at);
  const remainingMs = config.minIntervalMs - (now - createdAt);
  if (latest.status === 'queued' || latest.status === 'in_progress' || remainingMs > 0) {
    return Math.max(1, Math.ceil(Math.max(remainingMs, 60_000) / 60_000));
  }
  return 0;
}

async function dispatchWorkflow(config) {
  const path =
    `/repos/${config.owner}/${config.repo}/actions/workflows/` +
    `${config.workflowFile}/dispatches`;
  const response = await githubRequest(
    path,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ref: config.workflowRef }),
    },
    config.token,
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

  let config;
  try {
    config = readRuntimeConfig(process.env);
  } catch (error) {
    console.error(error.message);
    return sendJson(response, 503, {
      ok: false,
      message: '環境変数の設定値が不正です。Vercelの設定を確認してください。',
    });
  }

  if (!config) {
    console.error('Required Vercel environment variables are missing');
    return sendJson(response, 503, {
      ok: false,
      message: '更新機能の準備が完了していません。Vercelの環境変数（GITHUB_OWNER / GITHUB_REPO / GITHUB_TOKEN / UPDATE_PASSWORD_HASH）を確認してください。',
    });
  }

  let passwordMatches = false;
  try {
    passwordMatches = verifyPassphrase(request.body?.passphrase, config.expectedHash);
  } catch (error) {
    console.error(error.message);
    return sendJson(response, 503, {
      ok: false,
      message: '合言葉ハッシュの設定が不正です。64文字のSHA-256ハッシュを設定してください。',
    });
  }

  if (!passwordMatches) {
    return sendJson(response, 401, { ok: false, message: '合言葉が違います。' });
  }

  try {
    const cooldownMinutes = await getCooldownMinutes(config);
    if (cooldownMinutes > 0) {
      return sendJson(response, 429, {
        ok: false,
        message: `更新中または連続実行防止中です。約${cooldownMinutes}分後にお試しください。`,
      });
    }

    await dispatchWorkflow(config);
    return sendJson(response, 202, {
      ok: true,
      message: '更新を受け付けました。通常は1〜3分でスプレッドシートへ反映されます。',
    });
  } catch (error) {
    console.error(error.message);
    return sendJson(response, 502, {
      ok: false,
      message: '更新を開始できませんでした。GitHubトークンの有効期限や権限を確認してください。',
    });
  }
}

module.exports = handler;
module.exports._test = {
  dispatchWorkflow,
  getCooldownMinutes,
  isSameOrigin,
  readRuntimeConfig,
  verifyPassphrase,
};
