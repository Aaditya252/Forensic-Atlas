// Smart deployment switch:
// If running on localhost / 127.0.0.1, use 'api' mode with the local FastAPI backend.
// When deployed on Vercel or any remote domain (https), automatically use 'demo' mode 
// with the rich offline snapshot so the entire case workspace works seamlessly for any visitor!
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
