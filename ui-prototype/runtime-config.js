// Local deployment switch. Set dataMode to "api" and configure apiBaseUrl
// after a compatible backend has been started. Never place a secret here.
globalThis.SUTRAM_CONFIG = Object.freeze({
  dataMode: 'api',
  apiBaseUrl: globalThis.location.origin,
  apiTimeoutMs: 12000,
  caseId: 'DF-24-017'
});
