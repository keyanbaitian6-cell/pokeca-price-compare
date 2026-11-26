/**
 * Cloudflare Workers 無料枠（1日10万リクエスト・商用/副業利用OK）で動く
 * 「合言葉認証つき スマホ1タップ手動更新 API」
 *
 * Vercel Hobby は「個人の趣味・非商用限定」のため、副業・せどり・業務リサーチ等で
 * 使う場合はこちら（または GitHub 公式スマホアプリの Run workflow 直起動）を推奨します。
 *
 * 必要な Cloudflare Workers Secrets / Variables:
 *   - GITHUB_OWNER          : あなたのGitHubユーザー名
 *   - GITHUB_REPO           : 非公開リポジトリ名
 *   - GITHUB_TOKEN          : Fine-grained PAT (Actions: Read and write のみ)
 *   - UPDATE_PASSWORD_HASH  : 合言葉の64文字SHA-256ハッシュ (tools/config_builder.html で生成可)
 *   - WORKFLOW_FILE         : (任意) 既定 update-prices.yml
 *   - WORKFLOW_REF          : (任意) 既定 main
 *   - MIN_INTERVAL_MINUTES  : (任意) 最小5分
 */

const DEFAULT_WORKFLOW_FILE = 'update-prices.yml';
const DEFAULT_WORKFLOW_REF = 'main';
const MIN_SAFE_INTERVAL_MINUTES = 5;
const GITHUB_API_VERSION = '2022-11-28';
const SAFE_SEGMENT_RE = /^[a-zA-Z0-9._-]{1,100}$/;

function jsonResponse(status, body, extraHeaders = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Cache-Control': 'no-store',
      'Content-Type': 'application/json; charset=utf-8',
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
      'Referrer-Policy': 'no-referrer',
      ...extraHeaders,
    },
  });
}

function isSameOrigin(request) {
  const origin = request.headers.get('origin');
  const url = new URL(request.url);
  return Boolean(origin && origin === url.origin);
}

function constantTimeEqualHex(aHex, bHex) {
  if (aHex.length !== bHex.length) {
    return false;
  }
  let diff = 0;
  for (let i = 0; i < aHex.length; i += 1) {
    diff |= aHex.charCodeAt(i) ^ bHex.charCodeAt(i);
  }
  return diff === 0;
}

async function verifyPassphrase(passphrase, expectedHash) {
  if (typeof passphrase !== 'string' || passphrase.length === 0 || passphrase.length > 128) {
    return false;
  }
  if (!/^[a-f0-9]{64}$/i.test(expectedHash || '')) {
    throw new Error('UPDATE_PASSWORD_HASH is not a valid 64-char SHA-256 hex digest');
  }
  const encoded = new TextEncoder().encode(passphrase);
  const digestBuffer = await crypto.subtle.digest('SHA-256', encoded);
  const actualHex = Array.from(new Uint8Array(digestBuffer), (b) => b.toString(16).padStart(2, '0')).join('');
  return constantTimeEqualHex(actualHex.toLowerCase(), expectedHash.toLowerCase());
}

function readRuntimeConfig(env) {
  const owner = String(env.GITHUB_OWNER || '').trim();
  const repo = String(env.GITHUB_REPO || '').trim();
  const workflowFile = String(env.WORKFLOW_FILE || DEFAULT_WORKFLOW_FILE).trim();
  const workflowRef = String(env.WORKFLOW_REF || DEFAULT_WORKFLOW_REF).trim();
  const token = String(env.GITHUB_TOKEN || '').trim();
  const expectedHash = String(env.UPDATE_PASSWORD_HASH || '').trim();

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

function githubHeaders(token) {
  return {
    Accept: 'application/vnd.github+json',
    Authorization: `Bearer ${token}`,
    'X-GitHub-Api-Version': GITHUB_API_VERSION,
    'User-Agent': 'price-monitor-kit-cf-worker',
  };
}

async function getCooldownMinutes(config, now = Date.now(), fetchImpl = fetch) {
  const url =
    `https://api.github.com/repos/${config.owner}/${config.repo}/actions/workflows/` +
    `${config.workflowFile}/runs?per_page=1`;
  const response = await fetchImpl(url, { method: 'GET', headers: githubHeaders(config.token) });
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

async function dispatchWorkflow(config, fetchImpl = fetch) {
  const url =
    `https://api.github.com/repos/${config.owner}/${config.repo}/actions/workflows/` +
    `${config.workflowFile}/dispatches`;
  const response = await fetchImpl(url, {
    method: 'POST',
    headers: {
      ...githubHeaders(config.token),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      ref: config.workflowRef,
      inputs: { run_mode: 'production' },
    }),
  });
  if (response.status !== 204) {
    throw new Error(`GitHub workflow dispatch returned HTTP ${response.status}`);
  }
}

async function handleApiUpdate(request, env, fetchImpl = fetch) {
  if (request.method !== 'POST') {
    return jsonResponse(405, { ok: false, message: 'この操作には対応していません。' }, { Allow: 'POST' });
  }
  if (!isSameOrigin(request)) {
    return jsonResponse(403, { ok: false, message: 'このページから操作してください。' });
  }

  let config;
  try {
    config = readRuntimeConfig(env || {});
  } catch (error) {
    console.error(error.message);
    return jsonResponse(503, {
      ok: false,
      message: '環境変数の設定値が不正です。Cloudflare Workers の設定を確認してください。',
    });
  }
  if (!config) {
    return jsonResponse(503, {
      ok: false,
      message: '更新機能の準備が完了していません。環境変数（GITHUB_OWNER / GITHUB_REPO / GITHUB_TOKEN / UPDATE_PASSWORD_HASH）を確認してください。',
    });
  }

  let body;
  try {
    body = await request.json();
  } catch (_err) {
    return jsonResponse(400, { ok: false, message: 'リクエスト形式が不正です。' });
  }

  let matches = false;
  try {
    matches = await verifyPassphrase(body?.passphrase, config.expectedHash);
  } catch (error) {
    console.error(error.message);
    return jsonResponse(503, {
      ok: false,
      message: '合言葉ハッシュの設定が不正です。64文字のSHA-256ハッシュを設定してください。',
    });
  }
  if (!matches) {
    return jsonResponse(401, { ok: false, message: '合言葉が違います。' });
  }

  try {
    const cooldown = await getCooldownMinutes(config, Date.now(), fetchImpl);
    if (cooldown > 0) {
      return jsonResponse(429, {
        ok: false,
        message: `更新中または連続実行防止中です。約${cooldown}分後にお試しください。`,
      });
    }
    await dispatchWorkflow(config, fetchImpl);
    return jsonResponse(202, {
      ok: true,
      message: '更新を受け付けました。通常は1〜3分でスプレッドシートへ反映されます。',
    });
  } catch (error) {
    console.error(error.message);
    return jsonResponse(502, {
      ok: false,
      message: '更新を開始できませんでした。GitHubトークンの有効期限や権限を確認してください。',
    });
  }
}

const worker = {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === '/api/update') {
      return handleApiUpdate(request, env);
    }
    if (env && env.ASSETS && typeof env.ASSETS.fetch === 'function') {
      return env.ASSETS.fetch(request);
    }
    return new Response('Not Found', { status: 404 });
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = worker;
  module.exports._test = {
    dispatchWorkflow,
    getCooldownMinutes,
    handleApiUpdate,
    isSameOrigin,
    readRuntimeConfig,
    verifyPassphrase,
  };
}
