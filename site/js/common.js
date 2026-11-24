/**
 * トレカ損益ラボ — 共通UI・収益化レンダラー・フォーマットユーティリティ
 */
import {
  SITE_CONFIG,
  ADSENSE_CONFIG,
  hasActiveAffiliateLinks,
  getActiveOffers,
} from './monetization.js';

export function formatYen(value, { signed = false } = {}) {
  const n = Math.round(Number(value) || 0);
  const abs = Math.abs(n).toLocaleString('ja-JP');
  if (n < 0) return `-${abs}円`;
  if (signed && n > 0) return `+${abs}円`;
  return `${abs}円`;
}

export function formatPercent(value, { signed = false, digits = 1 } = {}) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '—';
  const fixed = Math.abs(n).toFixed(digits);
  if (n < 0) return `-${fixed}%`;
  if (signed && n > 0) return `+${fixed}%`;
  return `${fixed}%`;
}

export function escapeHtml(text) {
  return String(text ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

const NAV_ITEMS = [
  { id: 'home', href: './index.html', label: 'トップ' },
  { id: 'sell-compare', href: './sell-compare.html', label: 'フリマ vs 買取' },
  { id: 'psa', href: './psa.html', label: 'PSA鑑定 損益' },
  { id: 'oripa', href: './oripa.html', label: 'オリパ期待値' },
  { id: 'portfolio', href: './portfolio.html', label: 'BOX資産管理' },
];

/**
 * 共通ヘッダー・フッター・ステマ規制PR表記・AdSense制御を初期化
 */
export function initCommonChrome(activePageId) {
  // 1. PR表記（アフィリエイトURLが1件以上設定されている場合のみ自動表示）
  const prBar = document.getElementById('prDisclosureBar');
  if (prBar) {
    prBar.hidden = !hasActiveAffiliateLinks();
  }

  // 2. ナビゲーションの現在地設定とモバイルメニュー開閉
  document.querySelectorAll('.site-nav .nav-link').forEach((link) => {
    if (link.dataset.page === activePageId) {
      link.setAttribute('aria-current', 'page');
    } else {
      link.removeAttribute('aria-current');
    }
  });

  const navToggle = document.getElementById('navToggle');
  const siteNav = document.getElementById('siteNav');
  if (navToggle && siteNav) {
    navToggle.addEventListener('click', () => {
      const expanded = navToggle.getAttribute('aria-expanded') === 'true';
      navToggle.setAttribute('aria-expanded', String(!expanded));
      siteNav.classList.toggle('is-open', !expanded);
    });
  }

  // 3. フッターの運営名・Xリンク・更新日を同期
  document.querySelectorAll('[data-site-operator]').forEach((el) => {
    el.textContent = SITE_CONFIG.operatorName;
  });
  document.querySelectorAll('[data-site-updated]').forEach((el) => {
    el.textContent = SITE_CONFIG.lastUpdated;
  });
  document.querySelectorAll('[data-x-link]').forEach((el) => {
    if (SITE_CONFIG.xHandle) {
      const cleanHandle = SITE_CONFIG.xHandle.replace(/^@/, '');
      el.href = `https://x.com/${cleanHandle}`;
      el.textContent = `X（@${cleanHandle}）`;
      el.hidden = false;
    } else {
      el.hidden = true;
    }
  });

  // 4. Google AdSense（審査通過後に monetization.js で enabled: true にした時だけ読み込む）
  initAdSenseSlots();
}

function initAdSenseSlots() {
  const slots = document.querySelectorAll('[data-ad-slot]');
  if (!ADSENSE_CONFIG.enabled || !ADSENSE_CONFIG.clientId) {
    slots.forEach((slot) => {
      slot.hidden = true;
    });
    return;
  }

  // スクリプトを1回だけ挿入
  if (!document.querySelector('script[data-adsense-loader]')) {
    const script = document.createElement('script');
    script.async = true;
    script.dataset.adsenseLoader = 'true';
    script.src = `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${encodeURIComponent(ADSENSE_CONFIG.clientId)}`;
    script.crossOrigin = 'anonymous';
    document.head.appendChild(script);
  }

  slots.forEach((slotEl) => {
    const slotKey = slotEl.dataset.adSlot;
    const slotId = ADSENSE_CONFIG.slots[slotKey];
    if (!slotId) {
      slotEl.hidden = true;
      return;
    }
    slotEl.hidden = false;
    slotEl.innerHTML = `
      <div class="ad-label">スポンサーリンク</div>
      <ins class="adsbygoogle"
           style="display:block"
           data-ad-client="${escapeHtml(ADSENSE_CONFIG.clientId)}"
           data-ad-slot="${escapeHtml(slotId)}"
           data-ad-format="auto"
           data-full-width-responsive="true"></ins>
    `;
    try {
      (window.adsbygoogle = window.adsbygoogle || []).push({});
    } catch {
      // AdSense script still loading
    }
  });
}

/**
 * 計算結果に応じた文脈連動おすすめ枠（ASPリンク設定済みならPRカード、未設定なら実用アドバイスを表示）
 */
export function renderContextualRecommendation(container, { category, title, fallbackTip }) {
  if (!container) return;
  const offers = getActiveOffers(category);

  if (offers.length > 0) {
    const itemsHtml = offers
      .map(
        (offer) => `
      <div class="rec-item">
        <div class="rec-item-body">
          <h4>${escapeHtml(offer.title)} <span class="badge badge-gold">${escapeHtml(offer.badge)}</span></h4>
          <p>${escapeHtml(offer.description)}</p>
        </div>
        <a class="btn btn-primary btn-sm" href="${escapeHtml(offer.url)}" target="_blank" rel="sponsored noopener noreferrer">
          ${escapeHtml(offer.ctaText)} ↗
        </a>
      </div>`
      )
      .join('');

    container.innerHTML = `
      <div class="rec-head">
        <h3 class="rec-title">${escapeHtml(title)}</h3>
        <span class="pr-tag">PR</span>
      </div>
      <div class="rec-list">${itemsHtml}</div>
    `;
  } else {
    container.innerHTML = `
      <div class="rec-head">
        <h3 class="rec-title">${escapeHtml(title)}</h3>
        <span class="badge badge-muted">損益改善ヒント</span>
      </div>
      <p class="rec-tip">${escapeHtml(fallbackTip)}</p>
    `;
  }
}

/**
 * X（旧Twitter）シェアURL生成
 */
export function buildXShareUrl(text, pagePath = '') {
  const url = pagePath
    ? `${SITE_CONFIG.siteUrl.replace(/\/$/, '')}/${pagePath.replace(/^\//, '')}`
    : window.location.href;
  const fullText = SITE_CONFIG.xHandle
    ? `${text}\n${SITE_CONFIG.xHandle} #ポケカ #トレカ損益ラボ`
    : `${text}\n#ポケカ #トレカ損益ラボ`;
  const params = new URLSearchParams({ text: fullText, url });
  return `https://twitter.com/intent/tweet?${params.toString()}`;
}

/**
 * クリップボードコピー（フィードバック表示付き）
 */
export async function copyTextWithToast(text, toastEl) {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
    } else {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      ta.remove();
    }
    if (toastEl) {
      toastEl.textContent = '結果をコピーしました';
      clearTimeout(toastEl._timer);
      toastEl._timer = setTimeout(() => {
        toastEl.textContent = '';
      }, 2400);
    }
    return true;
  } catch {
    if (toastEl) {
      toastEl.textContent = 'コピーに失敗しました';
    }
    return false;
  }
}

export { NAV_ITEMS };
