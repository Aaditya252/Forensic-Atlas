// The public static deployment presents fictional demo data.
// The full backend is a separate persistent service; never imply it runs here.
const isLocalhost = typeof window !== 'undefined' && (
  window.location.hostname === 'localhost' ||
  window.location.hostname === '127.0.0.1' ||
  window.location.protocol === 'file:'
);

globalThis.SUTRAM_CONFIG = Object.freeze({
  dataMode: isLocalhost ? 'api' : 'demo',
  apiBaseUrl: isLocalhost ? 'http://127.0.0.1:8100' : '',
  apiTimeoutMs: 12000,
  caseId: 'DF-24-017'
});

if (!isLocalhost) {
  const notice = document.createElement('div');
  notice.setAttribute('role', 'status');
  notice.textContent = 'Interactive demo · Fictional case data. Live uploads, Qwen, graph memory and saved reports require the full backend.';
  notice.style.cssText = 'position:fixed;bottom:0;left:0;right:0;z-index:10000;padding:10px 18px;background:#152638;color:#fff;font:13px/1.5 system-ui;text-align:center;border-top:1px solid #6db7ad';
  document.body.appendChild(notice);
}
