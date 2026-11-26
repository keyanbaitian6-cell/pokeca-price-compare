/**
 * トレカ損益ラボ — 共通UI・スティッキー結果バー・収益化レンダラー
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

/**
 * 共通ヘッダー・常設4ツールタブバー・PR表記・フッター・AdSense制御を初期化
 */
export function initCommonChrome(activePageId) {
  const prBar = document.getElementById('prDisclosureBar');
  if (prBar) {
    prBar.hidden = !hasActiveAffiliateLinks();
  }

  document.querySelectorAll('.tool-tab-link, .site-nav .nav-link').forEach((link) => {
    const isMatch =
      link.dataset.page === activePageId ||
      (activePageId === 'sell-compare' && link.dataset.page === 'home');
    if (isMatch) {
      link.setAttribute('aria-current', 'page');
    } else {
      link.removeAttribute('aria-current');
    }
  });

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

  initAdSenseSlots();
}

/**
 * モバイル用スティッキーボトム結果バー（判定カードが画面外にスクロールされた時だけ自動出現）
 */
export function bindStickyMobileBar({ targetEl, barEl, scrollToSelector }) {
  if (!targetEl || !barEl || typeof IntersectionObserver === 'undefined') return;

  const observer = new IntersectionObserver(
    (entries) => {
      const entry = entries[0];
      barEl.classList.toggle('is-visible', !entry.isIntersecting);
    },
    { threshold: 0.15 }
  );
  observer.observe(targetEl);

  const jumpBtn = barEl.querySelector('[data-sticky-jump]');
  if (jumpBtn) {
    jumpBtn.addEventListener('click', () => {
      const dest = scrollToSelector ? document.querySelector(scrollToSelector) : targetEl;
      if (dest) {
        dest.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  }
}

function initAdSenseSlots() {
  const slots = document.querySelectorAll('[data-ad-slot]');
  if (!ADSENSE_CONFIG.enabled || !ADSENSE_CONFIG.clientId) {
    slots.forEach((slot) => {
      slot.hidden = true;
    });
    return;
  }

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
 * 計算結果に応じた文脈連動おすすめ枠
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
      toastEl.textContent = 'コピーしました';
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

export function saveJsonState(key, value) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // ignore storage errors
  }
}

export function loadJsonState(key) {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}
