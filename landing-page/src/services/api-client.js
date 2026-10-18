/** Small fetch wrapper with bounded waits and consistent API errors. */
export class ApiError extends Error {
  constructor(message, { status = 0, code = 'NETWORK_ERROR', requestId = null } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }
}

function makeRequestId() {
  return globalThis.crypto?.randomUUID?.() ?? `req-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function createApiClient({ baseUrl, timeoutMs = 12000, getAccessToken = async () => null }) {
  const normalizedBase = String(baseUrl || '').trim().replace(/\/+$/, '');
  if (!normalizedBase) throw new Error('API mode requires SUTRAM_CONFIG.apiBaseUrl.');
  let parsedBase;
  try { parsedBase = new URL(normalizedBase); }
  catch { throw new Error('SUTRAM_CONFIG.apiBaseUrl must be a valid HTTP or HTTPS URL.'); }
  if (!['http:', 'https:'].includes(parsedBase.protocol)) throw new Error('SUTRAM_CONFIG.apiBaseUrl must use HTTP or HTTPS.');
  if (!Number.isFinite(Number(timeoutMs)) || Number(timeoutMs) < 500 || Number(timeoutMs) > 120000) throw new Error('SUTRAM_CONFIG.apiTimeoutMs must be between 500 and 120000.');

  async function request(path, { method = 'GET', body, headers = {}, signal, idempotencyKey, timeoutMs: requestTimeoutMs = timeoutMs } = {}) {
    if (!Number.isFinite(Number(requestTimeoutMs)) || requestTimeoutMs < 500 || requestTimeoutMs > 120000) throw new Error('Request timeout must be between 500 and 120000 ms.');
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(new DOMException('Request timed out', 'TimeoutError')), requestTimeoutMs);
    const forwardAbort = () => controller.abort(signal.reason);
    if (signal) {
      if (signal.aborted) forwardAbort();
      else signal.addEventListener('abort', forwardAbort, { once: true });
    }

    const requestId = makeRequestId();
    try {
      const token = await getAccessToken();
      const requestHeaders = new Headers({ Accept: 'application/json', 'X-Request-Id': requestId, ...headers });
      const isFormData = typeof FormData !== 'undefined' && body instanceof FormData;
      if (body !== undefined && !isFormData) requestHeaders.set('Content-Type', 'application/json');
      if (token) requestHeaders.set('Authorization', `Bearer ${token}`);
      if (idempotencyKey) requestHeaders.set('Idempotency-Key', idempotencyKey);

      let response;
      try {
        response = await fetch(`${normalizedBase}${path.startsWith('/') ? path : `/${path}`}`, {
          method,
          headers: requestHeaders,
          body: body === undefined ? undefined : isFormData ? body : JSON.stringify(body),
          credentials: 'same-origin',
          cache: 'no-store',
          signal: controller.signal
        });
      } catch (error) {
        const timedOut = controller.signal.reason?.name === 'TimeoutError';
        if (controller.signal.aborted && !timedOut) throw new DOMException('Request was cancelled.', 'AbortError');
        throw new ApiError(timedOut ? 'The service did not respond in time.' : 'The service could not be reached.', {
          code: timedOut ? 'TIMEOUT' : 'NETWORK_ERROR', requestId
        });
      }

      const contentType = response.headers.get('content-type') || '';
      const payload = response.status === 204 ? null : contentType.includes('application/json') ? await response.json().catch(() => null) : null;
      if (!response.ok) {
        const message = payload?.error?.message || `The service returned ${response.status}.`;
        throw new ApiError(message, { status: response.status, code: payload?.error?.code || 'HTTP_ERROR', requestId: response.headers.get('x-request-id') || requestId });
      }
      return payload;
    } finally {
      clearTimeout(timeout);
      signal?.removeEventListener('abort', forwardAbort);
    }
  }

  return Object.freeze({ request });
}
