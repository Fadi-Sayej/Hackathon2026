const REALM = 'SmartShelf pilot'

function authChallenge() {
  return new Response('Authentication required', {
    status: 401,
    headers: {
      'WWW-Authenticate': `Basic realm="${REALM}", charset="UTF-8"`,
      'Cache-Control': 'no-store',
      'X-Robots-Tag': 'noindex, nofollow, noarchive',
    },
  })
}

function protectionNotConfigured() {
  return new Response('Deployment access protection is not configured.', {
    status: 503,
    headers: {
      'Cache-Control': 'no-store',
      'X-Robots-Tag': 'noindex, nofollow, noarchive',
    },
  })
}

function parseBasicAuth(header) {
  if (!header?.startsWith('Basic ')) return null

  try {
    const decoded = atob(header.slice('Basic '.length))
    const separator = decoded.indexOf(':')
    if (separator < 0) return null

    return {
      user: decoded.slice(0, separator),
      password: decoded.slice(separator + 1),
    }
  } catch {
    return null
  }
}

export default function middleware(request) {
  const expectedUser = process.env.BASIC_AUTH_USER
  const expectedPassword = process.env.BASIC_AUTH_PASSWORD

  if (!expectedUser || !expectedPassword) {
    return protectionNotConfigured()
  }

  const credentials = parseBasicAuth(request.headers.get('authorization'))
  if (
    credentials?.user !== expectedUser ||
    credentials.password !== expectedPassword
  ) {
    return authChallenge()
  }
}

export const config = {
  matcher: '/(.*)',
}
