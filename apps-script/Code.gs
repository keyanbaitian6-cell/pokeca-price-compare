const DEFAULTS = Object.freeze({
  WORKFLOW_FILE: 'manual-update.yml',
  WORKFLOW_REF: 'main',
  MIN_INTERVAL_SECONDS: '300',
  OUTPUT_SPREADSHEET_ID: '1N3mF4tIjuq8FC3JO5QnT2rPKPn-tu3I8lFLP8ZNysYI',
});

function doGet() {
  return HtmlService.createTemplateFromFile('Index')
    .evaluate()
    .setTitle('ポケカ買取価格表を更新')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

/**
 * Checks the shared passphrase server-side and dispatches one GitHub Actions run.
 * GitHub tokens and the expected passphrase are kept in Script Properties and
 * are never sent to the browser.
 */
function startUpdate(passphrase) {
  const config = getConfig_();
  if (!constantTimeEquals_(String(passphrase || ''), config.UPDATE_PASSWORD)) {
    return { ok: false, message: '合言葉が違います。' };
  }

  const lock = LockService.getScriptLock();
  if (!lock.tryLock(1000)) {
    return { ok: false, message: '別の更新を受け付けています。少し待ってからお試しください。' };
  }

  try {
    const properties = PropertiesService.getScriptProperties();
    const now = Date.now();
    const lastDispatchAt = Number(properties.getProperty('LAST_DISPATCH_AT') || 0);
    const minimumIntervalMs = Number(config.MIN_INTERVAL_SECONDS) * 1000;
    const remainingMs = minimumIntervalMs - (now - lastDispatchAt);
    if (remainingMs > 0) {
      const remainingMinutes = Math.max(1, Math.ceil(remainingMs / 60000));
      return {
        ok: false,
        message: `連続実行を防ぐため、あと約${remainingMinutes}分お待ちください。`,
      };
    }

    const endpoint =
      `https://api.github.com/repos/${encodeURIComponent(config.GITHUB_OWNER)}/` +
      `${encodeURIComponent(config.GITHUB_REPO)}/actions/workflows/` +
      `${encodeURIComponent(config.WORKFLOW_FILE)}/dispatches`;
    const response = UrlFetchApp.fetch(endpoint, {
      method: 'post',
      contentType: 'application/json',
      headers: {
        Accept: 'application/vnd.github+json',
        Authorization: `Bearer ${config.GITHUB_TOKEN}`,
        'X-GitHub-Api-Version': '2026-03-10',
      },
      payload: JSON.stringify({ ref: config.WORKFLOW_REF }),
      muteHttpExceptions: true,
    });

    const responseCode = response.getResponseCode();
    if (responseCode !== 200 && responseCode !== 204) {
      console.error(`GitHub Actions dispatch failed with HTTP ${responseCode}`);
      return {
        ok: false,
        message: `更新を開始できませんでした（HTTP ${responseCode}）。管理者に連絡してください。`,
      };
    }

    properties.setProperty('LAST_DISPATCH_AT', String(now));
    return {
      ok: true,
      message: '更新を受け付けました。通常は数分で価格表へ反映されます。',
      sheetUrl: `https://docs.google.com/spreadsheets/d/${config.OUTPUT_SPREADSHEET_ID}/edit`,
    };
  } finally {
    lock.releaseLock();
  }
}

function getConfig_() {
  const properties = PropertiesService.getScriptProperties().getProperties();
  const config = Object.assign({}, DEFAULTS, properties);
  const required = ['GITHUB_OWNER', 'GITHUB_REPO', 'GITHUB_TOKEN', 'UPDATE_PASSWORD'];
  const missing = required.filter((key) => !config[key]);
  if (missing.length) {
    throw new Error(`Script Propertiesが不足しています: ${missing.join(', ')}`);
  }
  return config;
}

function constantTimeEquals_(left, right) {
  const leftDigest = Utilities.computeDigest(
    Utilities.DigestAlgorithm.SHA_256,
    left,
    Utilities.Charset.UTF_8,
  );
  const rightDigest = Utilities.computeDigest(
    Utilities.DigestAlgorithm.SHA_256,
    right,
    Utilities.Charset.UTF_8,
  );
  let difference = leftDigest.length ^ rightDigest.length;
  const length = Math.max(leftDigest.length, rightDigest.length);
  for (let index = 0; index < length; index += 1) {
    difference |= (leftDigest[index] || 0) ^ (rightDigest[index] || 0);
  }
  return difference === 0;
}
