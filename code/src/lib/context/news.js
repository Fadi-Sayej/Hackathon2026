/**
 * Local/world news signals via GDELT DOC 2.0 API.
 * Docs: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
 *
 * Free, no key. We pull a small set of recent article headlines that
 * mention the configured query (default: a country name) so the AI
 * layer can mention upcoming events that may affect demand.
 */

const BASE_URL = 'https://api.gdeltproject.org/api/v2/doc/doc'

function readEnv() {
  const env = typeof import.meta !== 'undefined' ? import.meta.env ?? {} : {}
  return {
    query: env.VITE_NEWS_QUERY || 'Jordan',
  }
}

export async function fetchNewsHeadlines({ query, max = 5, timespan = '24h', signal } = {}) {
  const q = query ?? readEnv().query
  const params = new URLSearchParams({
    query: q,
    mode: 'ArtList',
    format: 'json',
    maxrecords: String(max),
    timespan,
    sort: 'DateDesc',
  })
  const response = await fetch(`${BASE_URL}?${params.toString()}`, {
    signal,
  })
  if (!response.ok) {
    throw new Error(`GDELT request failed (${response.status})`)
  }
  let data
  try {
    data = await response.json()
  } catch {
    return []
  }
  const articles = Array.isArray(data?.articles) ? data.articles : []
  return articles.map((article) => ({
    title: article.title,
    url: article.url,
    source: article.domain ?? article.sourceCommonName ?? null,
    seenAt: article.seendate ?? null,
    language: article.language ?? null,
    tone: article.tone ?? null,
  }))
}

/**
 * Returns true if any headline mentions a keyword that typically shifts
 * convenience-store demand (sport event, festival, protest, heatwave...).
 * Useful as a quick boolean for the marketContext.
 */
export function hasDemandSignal(headlines, keywords = DEFAULT_KEYWORDS) {
  if (!Array.isArray(headlines) || headlines.length === 0) return null
  const lower = keywords.map((k) => k.toLowerCase())
  return headlines.find((article) => {
    const title = (article.title ?? '').toLowerCase()
    return lower.some((keyword) => title.includes(keyword))
  }) ?? null
}

const DEFAULT_KEYWORDS = [
  'match',
  'final',
  'derby',
  'football',
  'concert',
  'festival',
  'heatwave',
  'storm',
  'strike',
  'holiday',
]
