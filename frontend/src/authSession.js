export const SESSION_TOKEN_KEY = 'careerpath.session-token';
export const accountLabel = user => user?.email || 'Account';

export async function authenticateSession(api, mode, credentials, storage = globalThis.sessionStorage, fetchImpl = globalThis.fetch) {
  const response = await fetchImpl(`${api}/${mode}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(credentials) });
  const login = await response.json();
  if (!response.ok) throw new Error(login.error || 'Authentication failed');
  const identityResponse = await fetchImpl(`${api}/auth/me`, { headers: { Authorization: `Bearer ${login.token}` } });
  const identity = await identityResponse.json();
  if (!identityResponse.ok) throw new Error(identity.error || 'Could not verify the authenticated account');
  if (!identity.email || !identity.role) throw new Error('The server did not return an authenticated email and role');
  rememberSession(login.token, storage);
  return { ...login, ...identity, token: login.token, password: '' };
}

export async function restoreSession(api, storage = globalThis.sessionStorage, fetchImpl = globalThis.fetch) {
  const token = storage?.getItem(SESSION_TOKEN_KEY);
  if (!token) return null;
  try {
    const response = await fetchImpl(`${api}/auth/me`, { headers: { Authorization: `Bearer ${token}` } });
    if (!response.ok) throw new Error('Session is no longer valid');
    const user = await response.json();
    return { ...user, token, password: '' };
  } catch {
    storage?.removeItem(SESSION_TOKEN_KEY);
    return null;
  }
}

export function rememberSession(token, storage = globalThis.sessionStorage) {
  if (token) storage?.setItem(SESSION_TOKEN_KEY, token);
  else storage?.removeItem(SESSION_TOKEN_KEY);
}

export async function logoutSession(api, token, storage = globalThis.sessionStorage, fetchImpl = globalThis.fetch) {
  try {
    if (token) await fetchImpl(`${api}/auth/logout`, { method: 'POST', headers: { Authorization: `Bearer ${token}` } });
  } finally {
    storage?.removeItem(SESSION_TOKEN_KEY);
  }
}
