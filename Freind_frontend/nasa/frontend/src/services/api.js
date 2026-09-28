/**
 * Centralized API service for SPHEREx Moving Object Explorer.
 * Connects frontend to the FastAPI backend.
 */

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');

/**
 * Custom API error with structured backend details.
 */
export class ApiError extends Error {
  constructor(message, status, detail = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Generic fetch wrapper with timeout and JSON error parsing.
 */
async function fetchJson(endpoint, options = {}, timeoutMs = 45000) {
  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Accept': 'application/json',
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...options.headers,
      },
    });
    clearTimeout(timer);

    if (!res.ok) {
      let detail = null;
      try {
        const errorJson = await res.json();
        detail = errorJson.detail || errorJson;
      } catch {
        detail = await res.text();
      }

      let errorMsg = `Server error (${res.status})`;
      if (typeof detail === 'string') {
        errorMsg = detail;
      } else if (detail && detail.message) {
        errorMsg = detail.message;
      } else if (Array.isArray(detail)) {
        errorMsg = detail.map(d => d.msg || JSON.stringify(d)).join(', ');
      }

      throw new ApiError(errorMsg, res.status, detail);
    }

    return await res.json();
  } catch (err) {
    clearTimeout(timer);
    if (err.name === 'AbortError') {
      throw new ApiError('Request timed out. NASA/IRSA or FITS processing took too long.', 504);
    }
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(
      `Network connection failed. Backend might be unreachable at ${API_BASE_URL}.`,
      0,
      err.message
    );
  }
}

/**
 * 1. Health Check
 * GET /api/health
 * @returns {Promise<{ status: string, service: string }>}
 */
export async function checkBackendHealth() {
  return await fetchJson('/api/health', { method: 'GET' }, 8000);
}

/**
 * 2. Search SPHEREx Archive
 * GET /api/search?ra=...&dec=...&radius_arcmin=...&start_date=...&end_date=...
 * @param {Object} params
 * @param {number} params.ra - Right Ascension (0 to 360)
 * @param {number} params.dec - Declination (-90 to 90)
 * @param {number} [params.radius_arcmin=10.0] - Search radius (0.1 to 120 arcmin)
 * @param {string} [params.start_date] - Optional start date YYYY-MM-DD
 * @param {string} [params.end_date] - Optional end date YYYY-MM-DD
 * @returns {Promise<{ query: Object, count: number, observations: Array }>}
 */
export async function searchObservations({
  ra,
  dec,
  radius_arcmin = 10.0,
  start_date,
  end_date,
}) {
  const query = new URLSearchParams({
    ra: String(ra),
    dec: String(dec),
    radius_arcmin: String(radius_arcmin),
  });

  if (start_date) query.set('start_date', start_date);
  if (end_date) query.set('end_date', end_date);

  return await fetchJson(`/api/search?${query.toString()}`, { method: 'GET' }, 60000);
}

/**
 * 3. Fetch SPHEREx Cutout
 * POST /api/cutout
 * @param {Object} cutoutParams
 * @returns {Promise<Object>} Cutout metadata and cached file paths
 */
export async function fetchCutout(cutoutParams) {
  return await fetchJson('/api/cutout', {
    method: 'POST',
    body: JSON.stringify(cutoutParams)
  }, 90000);
}

/**
 * 4. Run Two-Epoch Motion Analysis
 * POST /api/analyze-motion
 * @param {Object} analysisRequest
 * @returns {Promise<Object>} Motion analysis results with candidates & statistics
 */
export async function analyzeMotion(analysisRequest) {
  return await fetchJson('/api/analyze-motion', {
    method: 'POST',
    body: JSON.stringify(analysisRequest)
  }, 90000);
}

/**
 * 5. Validate Known Object (3I/ATLAS)
 * GET /api/known-object/3i-atlas
 * @returns {Promise<Object>} 3I/ATLAS validation response
 */
export async function validateKnownObject3IAtlas() {
  return await fetchJson('/api/known-object/3i-atlas', { method: 'GET' }, 90000);
}

/**
 * 6. Get safe browser preview URL for generated PNGs
 * @param {string} filenameOrPath
 * @returns {string} URL to preview image
 */
export function getPreviewUrl(filenameOrPath) {
  if (!filenameOrPath) return '';
  if (filenameOrPath.startsWith('http://') || filenameOrPath.startsWith('https://')) {
    return filenameOrPath;
  }
  // Strip any directory prefixes if full path was provided
  const filename = filenameOrPath.split(/[\\/]/).pop();
  return `${API_BASE_URL}/api/preview/${encodeURIComponent(filename)}`;
}

/**
 * 7. Get Challenge Demonstration Scenarios
 * GET /api/hypothesis/scenarios
 * @returns {Promise<Array>} List of pre-configured challenge scenarios
 */
export async function fetchChallengeScenarios() {
  return await fetchJson('/api/hypothesis/scenarios', { method: 'GET' }, 15000);
}

/**
 * 8. Evaluate Hypothesis Update with New Observation
 * POST /api/hypothesis/update
 * @param {Object} payload - HypothesisUpdateRequest
 * @returns {Promise<Object>} HypothesisUpdateResult
 */
export async function updateHypothesis(payload) {
  return await fetchJson('/api/hypothesis/update', {
    method: 'POST',
    body: JSON.stringify(payload),
  }, 30000);
}

export { API_BASE_URL };
