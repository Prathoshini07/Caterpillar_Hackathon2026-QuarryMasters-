/**
 * Frontend API Service for Caterpillar Demand Forecasting ML API
 */

async function fetchApi(endpoint) {
  const urls = [
    `/api/forecast${endpoint}`,
    `http://localhost:8000/api/forecast${endpoint}`,
    `http://127.0.0.1:8000/api/forecast${endpoint}`
  ];

  let lastError = null;

  for (const url of urls) {
    try {
      const res = await fetch(url, {
        headers: { 'Accept': 'application/json' }
      });
      if (res.ok) {
        const data = await res.json();
        // Unwraps data if nested under .data or returns raw JSON
        return data?.data !== undefined ? data.data : data;
      } else {
        let detail = `HTTP ${res.status}`;
        try {
          const errJson = await res.json();
          if (errJson?.detail) detail = errJson.detail;
        } catch (_) {}
        lastError = new Error(detail);
      }
    } catch (err) {
      lastError = err;
    }
  }

  throw lastError || new Error(`Failed to fetch ${endpoint}`);
}

export async function getForecastStatus() {
  return fetchApi('/status');
}

export async function getAllForecasts() {
  return fetchApi('/all');
}

export async function getShortageForecasts() {
  return fetchApi('/shortages');
}

export async function getSiteForecasts(siteId) {
  if (!siteId || siteId === 'ALL') {
    return getAllForecasts();
  }
  return fetchApi(`/site/${encodeURIComponent(siteId)}`);
}

export async function getSingleForecast(siteId, equipmentType) {
  return fetchApi(`/site/${encodeURIComponent(siteId)}/equipment/${encodeURIComponent(equipmentType)}`);
}

export async function generateForecasts() {
  const urls = [
    '/api/forecast/generate',
    'http://localhost:8000/api/forecast/generate',
    'http://127.0.0.1:8000/api/forecast/generate'
  ];

  let lastError = null;

  for (const url of urls) {
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        }
      });
      if (res.ok) {
        const data = await res.json();
        return data?.data !== undefined ? data.data : data;
      } else {
        let detail = `HTTP ${res.status}`;
        try {
          const errJson = await res.json();
          if (errJson?.detail) detail = errJson.detail;
        } catch (_) {}
        lastError = new Error(detail);
      }
    } catch (err) {
      lastError = err;
    }
  }

  throw lastError || new Error('Failed to generate forecasts');
}
