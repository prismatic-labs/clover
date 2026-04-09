/**
 * Clover Embeddable Widget
 * https://prismatic-labs.github.io/clover/
 *
 * Usage:
 *   <div data-clover-stressor="housing_cost_burden" data-clover-country="US"></div>
 *   <script src="https://prismatic-labs.github.io/clover/widget.js" async></script>
 *
 * Attributes:
 *   data-clover-stressor  Stressor ID (e.g. "housing_cost_burden", "unemployment")
 *   data-clover-country   ISO country code: US GB DE FR IT JP AU CA SE NL (default: US)
 *   data-clover-theme     "light" (default) | "dark"
 *
 * The widget is self-contained — CSS is injected inline.
 * Data is fetched once and shared across all instances on a page.
 * Crisis resources link is always included.
 */
(function () {
  'use strict';

  const BASE     = 'https://prismatic-labs.github.io/clover/';
  const DATA_URL = BASE + 'data/stressors.json';

  // Warm, kind palette for mental health
  const SEV_COLOR = { extreme: '#B85A5A', high: '#C4854A', moderate: '#A08A3E', low: '#5B8A6F' };
  const SEV_BG    = { extreme: '#FDF0F0', high: '#FEF4EC', moderate: '#FDFAED', low: '#F0F6F2' };

  // ── Shared data promise (fetch once per page) ─────────────────────────────
  let _dataPromise = null;
  function getData() {
    if (!_dataPromise) {
      _dataPromise = fetch(DATA_URL).then(r => {
        if (!r.ok) throw new Error('clover widget: failed to load data');
        return r.json();
      });
    }
    return _dataPromise;
  }

  // ── Helpers ───────────────────────────────────────────────────────────────
  function countryPressure(stressor, country) {
    const raw = Math.min(99, Math.round(stressor.pressure_index * country.impact_multiplier));
    if (country.data_confidence === 'low')    return Math.min(99, Math.round(raw / 10) * 10) || 10;
    if (country.data_confidence === 'medium') return Math.min(99, Math.round(raw / 5)  * 5)  || 5;
    return raw;
  }
  function severityFromPct(pct) {
    if (pct >= 60) return 'extreme';
    if (pct >= 40) return 'high';
    if (pct >= 20) return 'moderate';
    return 'low';
  }
  function esc(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // ── CSS (injected once) ───────────────────────────────────────────────────
  let _cssInjected = false;
  function injectCSS() {
    if (_cssInjected) return;
    _cssInjected = true;
    const style = document.createElement('style');
    style.textContent = `
      .clover-widget {
        display: inline-block;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
        border-radius: 10px;
        border: 1px solid #E0D8D0;
        overflow: hidden;
        max-width: 260px;
        width: 100%;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        text-decoration: none;
        color: inherit;
        vertical-align: top;
      }
      .clover-widget[data-clover-theme="dark"] { border-color: rgba(255,255,255,0.15); }
      .clover-widget-inner { padding: 0.85rem 1rem; }
      .clover-widget-header { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.6rem; }
      .clover-widget-emoji { font-size: 1.5rem; line-height: 1; }
      .clover-widget-name { font-size: 0.88rem; font-weight: 700; }
      .clover-widget-cat  { font-size: 0.7rem; color: #7A7470; margin-top: 1px; }
      .clover-widget-badge {
        display: inline-block;
        padding: 1px 7px;
        border-radius: 20px;
        font-size: 0.65rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #fff;
        margin-bottom: 0.5rem;
      }
      .clover-widget-pct-row { display: flex; align-items: baseline; gap: 0.4rem; margin-bottom: 0.4rem; }
      .clover-widget-pct { font-size: 1.8rem; font-weight: 900; line-height: 1; }
      .clover-widget-pct-label { font-size: 0.7rem; color: #7A7470; line-height: 1.3; }
      .clover-widget-bar { height: 5px; background: #E0D8D0; border-radius: 3px; overflow: hidden; margin-bottom: 0.55rem; }
      .clover-widget-bar-fill { height: 100%; border-radius: 3px; }
      .clover-widget-drivers { font-size: 0.68rem; color: #6B6560; line-height: 1.5; }
      .clover-widget-crisis {
        padding: 0.35rem 1rem;
        font-size: 0.58rem;
        text-align: center;
        background: #F5F0EB;
        border-top: 1px solid #E0D8D0;
        color: #7A7470;
      }
      .clover-widget-crisis a { color: #5B4A6B; text-decoration: underline; text-underline-offset: 1px; }
      .clover-widget-footer {
        padding: 0.4rem 1rem;
        font-size: 0.62rem;
        text-align: right;
        border-top: 1px solid #E0D8D0;
        background: rgba(0,0,0,0.02);
      }
      .clover-widget-footer a { color: #5B4A6B; text-decoration: none; font-weight: 600; }
      .clover-widget-footer a:hover { text-decoration: underline; }
      .clover-widget-error {
        padding: 0.85rem 1rem;
        font-size: 0.75rem;
        color: #7A7470;
        font-family: -apple-system, sans-serif;
      }
      .clover-widget[data-clover-theme="dark"] .clover-widget-inner { background: #3D3548; color: #FAF7F2; }
      .clover-widget[data-clover-theme="dark"] .clover-widget-bar { background: rgba(255,255,255,0.12); }
      .clover-widget[data-clover-theme="dark"] .clover-widget-crisis { background: rgba(0,0,0,0.15); border-color: rgba(255,255,255,0.1); }
      .clover-widget[data-clover-theme="dark"] .clover-widget-crisis a { color: #D4A0A0; }
      .clover-widget[data-clover-theme="dark"] .clover-widget-footer { background: rgba(0,0,0,0.2); border-color: rgba(255,255,255,0.1); }
      .clover-widget[data-clover-theme="dark"] .clover-widget-footer a { color: #D4A0A0; }
      .clover-widget[data-clover-theme="dark"] .clover-widget-cat,
      .clover-widget[data-clover-theme="dark"] .clover-widget-pct-label,
      .clover-widget[data-clover-theme="dark"] .clover-widget-drivers { color: rgba(250,247,242,0.55); }
    `;
    document.head.appendChild(style);
  }

  // ── Render one element ────────────────────────────────────────────────────
  function renderWidget(el, data) {
    const stressorId = el.getAttribute('data-clover-stressor');
    const cc         = (el.getAttribute('data-clover-country') || 'US').toUpperCase();
    const theme      = el.getAttribute('data-clover-theme') || 'light';

    const stressor = data.stressors.find(s => s.id === stressorId);
    const country  = data.countries.find(c => c.code === cc) || data.countries[0];

    if (!stressor) {
      el.innerHTML = `<div class="clover-widget-error">Stressor "${esc(stressorId)}" not found. <a href="${BASE}" target="_blank" rel="noopener">Browse all</a></div>`;
      el.classList.add('clover-widget');
      return;
    }

    const pct   = countryPressure(stressor, country);
    const sev   = severityFromPct(pct);
    const color = SEV_COLOR[sev];
    const bg    = theme === 'dark' ? 'transparent' : SEV_BG[sev];
    const topDrivers = stressor.drivers.slice(0, 3).map(d =>
      `${d.input} ${d.change_pct >= 0 ? '+' : ''}${d.change_pct}%`
    ).join(' · ');

    el.setAttribute('data-clover-theme', theme);
    el.classList.add('clover-widget');
    el.innerHTML = `
      <div class="clover-widget-inner" style="background:${bg}">
        <div class="clover-widget-header">
          <span class="clover-widget-emoji">${stressor.emoji}</span>
          <div>
            <div class="clover-widget-name">${esc(stressor.name)}</div>
            <div class="clover-widget-cat">${esc(stressor.category)} · ${esc(country.name)}</div>
          </div>
        </div>
        <span class="clover-widget-badge" style="background:${color}">${sev} pressure</span>
        <div class="clover-widget-pct-row">
          <span class="clover-widget-pct" style="color:${color}">${pct}%</span>
          <span class="clover-widget-pct-label">pressure<br>index</span>
        </div>
        <div class="clover-widget-bar">
          <div class="clover-widget-bar-fill" style="width:${pct}%;background:${color}"></div>
        </div>
        <div class="clover-widget-drivers">${esc(topDrivers)}</div>
      </div>
      <div class="clover-widget-crisis">
        In crisis? <a href="https://findahelpline.com" target="_blank" rel="noopener">Find a helpline</a>
      </div>
      <div class="clover-widget-footer">
        <a href="${BASE}#${esc(stressorId)}" target="_blank" rel="noopener">Full breakdown → clover</a>
      </div>
    `;
  }

  // ── Main: find all host elements and populate ─────────────────────────────
  function run() {
    const elements = document.querySelectorAll('[data-clover-stressor]');
    if (!elements.length) return;

    injectCSS();

    getData().then(data => {
      elements.forEach(el => renderWidget(el, data));
    }).catch(err => {
      console.warn(err);
      elements.forEach(el => {
        el.classList.add('clover-widget');
        el.innerHTML = '<div class="clover-widget-error">Failed to load Clover data.</div>';
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();
