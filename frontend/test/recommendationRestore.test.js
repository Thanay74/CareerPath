import test from 'node:test';
import assert from 'node:assert/strict';
import { loadStudentWorkspace } from '../src/studentWorkspace.js';
import { profileSnapshot, recommendationView } from '../src/recommendationView.js';

function reply(body, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

test('restoration loads the authenticated profile before accepting a current snapshot', async () => {
  const calls = [];
  const saved = [{ career_id: 'C01', career_name: 'Example', compatibility_score: 78 }];
  const workspace = await loadStudentWorkspace('/api', { student_id: 'STU000005', token: 'only-this-student' }, async url => {
    calls.push(url);
    if (url.includes('/student/profile')) return reply({ profile: { education_level: '12th', subjects: { mathematics: 0 } } });
    if (url.includes('/recommendations')) return reply({ freshness: 'current', snapshot: { snapshot_id: 'snap-1' }, recommendations: saved });
    return reply({ attempts: [] });
  });
  assert.match(calls[0], /student\/profile\?student_id=STU000005/);
  assert.match(calls[1], /recommendations\?student_id=STU000005/);
  assert.deepEqual(workspace.recommendationState.recommendations, saved);
  assert.equal(workspace.recommendationState.freshness, 'current');
  const key = profileSnapshot(workspace.profile);
  assert.equal(recommendationView({ authenticated: true, resultCount: saved.length,
    resultToken: 'only-this-student', activeToken: 'only-this-student', resultProfile: key, activeProfile: key }), 'results');
});

test('stale, legacy, absent and malformed states never expose recommendation arrays', async t => {
  for (const response of [
    { freshness: 'stale', recommendations: [{ career_name: 'old' }] },
    { freshness: 'unverified', recommendations: [{ career_name: 'legacy' }] },
    { freshness: 'none', recommendations: [] },
    { recommendations: [{ career_name: 'unmarked' }] },
  ]) {
    await t.test(response.freshness || 'missing freshness', async () => {
      const workspace = await loadStudentWorkspace('/api', { student_id: 'STU000006', token: 'token' }, async url =>
        url.includes('/student/profile') ? reply({ profile: { education_level: '10th' } })
          : url.includes('/recommendations') ? reply(response) : reply({ attempts: [] }));
      assert.notEqual(workspace.recommendationState.freshness, 'current');
      assert.deepEqual(workspace.recommendationState.recommendations, []);
    });
  }
});

test('a retrieval failure is reported separately without losing loaded profile', async () => {
  const workspace = await loadStudentWorkspace('/api', { student_id: 'STU000007', token: 'token' }, async url =>
    url.includes('/student/profile') ? reply({ profile: { education_level: 'Bachelor\'s' } })
      : url.includes('/recommendations') ? reply({ error: 'temporary failure' }, 503) : reply({ attempts: [] }));
  assert.equal(workspace.profile.education_level, "Bachelor's");
  assert.equal(workspace.recommendationState.freshness, 'error');
  assert.match(workspace.recommendationState.message, /temporary failure/);
});

test('an expired session during restoration fails closed for profile and snapshots', async () => {
  await assert.rejects(loadStudentWorkspace('/api', { student_id: 'STU000008', token: 'expired' }, async url =>
    url.includes('/student/profile') ? reply({ profile: { education_level: '10th' } })
      : url.includes('/recommendations') ? reply({ error: 'unauthorized' }, 401) : reply({ attempts: [] })), error => error.status === 401);
});
