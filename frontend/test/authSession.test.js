import test from 'node:test';
import assert from 'node:assert/strict';
import { SESSION_TOKEN_KEY, restoreSession, rememberSession, logoutSession, authenticateSession } from '../src/authSession.js';

function storage() {
  const values = new Map();
  return { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) };
}

test('restores the backend identity only after validating the stored bearer token', async () => {
  const store = storage(); rememberSession('token-1', store);
  let called;
  const session = await restoreSession('/api', store, async (url, options) => {
    called = [url, options.headers.Authorization];
    return { ok: true, json: async () => ({ email: 'student@example.test', role: 'student', student_id: 42 }) };
  });
  assert.deepEqual(called, ['/api/auth/me', 'Bearer token-1']);
  assert.equal(session.email, 'student@example.test');
  assert.equal(session.role, 'student');
  assert.equal(session.student_id, 42);
});

test('clears expired sessions and revokes the bearer token at logout', async () => {
  const store = storage(); rememberSession('expired', store);
  assert.equal(await restoreSession('/api', store, async () => ({ ok: false })), null);
  assert.equal(store.getItem(SESSION_TOKEN_KEY), null);
  rememberSession('active', store);
  let request;
  await logoutSession('/api', 'active', store, async (url, options) => { request = [url, options.method, options.headers.Authorization]; return { ok: true }; });
  assert.deepEqual(request, ['/api/auth/logout', 'POST', 'Bearer active']);
  assert.equal(store.getItem(SESSION_TOKEN_KEY), null);
});

test('login uses the authenticated identity endpoint for the header account data', async () => {
  const store = storage(); const calls = [];
  const fetchMock = async (url, options) => {
    calls.push([url, options.method || 'GET', options.headers.Authorization]);
    if (url.endsWith('/login')) return { ok: true, json: async () => ({ token: 'new-token', role: 'student', student_id: 7 }) };
    return { ok: true, json: async () => ({ email: 'verified@example.test', role: 'student', student_id: 7 }) };
  };
  const session = await authenticateSession('/api', 'login', { email: 'input@example.test', password: 'password123' }, store, fetchMock);
  assert.equal(session.email, 'verified@example.test');
  assert.equal(session.role, 'student');
  assert.equal(store.getItem(SESSION_TOKEN_KEY), 'new-token');
  assert.deepEqual(calls, [['/api/login','POST',undefined],['/api/auth/me','GET','Bearer new-token']]);
});
