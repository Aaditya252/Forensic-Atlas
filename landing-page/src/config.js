/**
 * Runtime configuration for the standalone dashboard.
 *
 * Switch dataMode to "api" and set apiBaseUrl to connect a compatible backend.
 * Authentication is injected by the host application through
 * window.SUTRAM_AUTH.getAccessToken; credentials are never kept in localStorage.
 */
const supplied = globalThis.SUTRAM_CONFIG ?? {};
const selectedCase = new URLSearchParams(globalThis.location?.search || '').get('case');
if(selectedCase && !/^[A-Za-z0-9_-]{1,64}$/.test(selectedCase)) throw new Error('Invalid case selector.');

export const config = Object.freeze({
  dataMode: supplied.dataMode ?? 'demo',
  apiBaseUrl: supplied.apiBaseUrl ?? '',
  apiTimeoutMs: supplied.apiTimeoutMs ?? 12000,
  caseId: selectedCase || supplied.caseId || 'DF-24-017',
  getAccessToken: supplied.getAccessToken ?? (() => globalThis.SUTRAM_AUTH?.getAccessToken?.())
});

if (!['demo', 'api'].includes(config.dataMode)) {
  throw new Error('SUTRAM_CONFIG.dataMode must be "demo" or "api".');
}
