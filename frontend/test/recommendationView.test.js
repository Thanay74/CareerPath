import test from 'node:test';
import assert from 'node:assert/strict';
import { profileSnapshot, recommendationView } from '../src/recommendationView.js';

const profile = { education_level: '12th', interests: { technology: null } };

test('guest sees a sign-in prompt only after requesting personal matches', () => {
  assert.equal(recommendationView({ authenticated: false, promptRequested: false, resultCount: 0 }), 'empty');
  assert.equal(recommendationView({ authenticated: false, promptRequested: true, resultCount: 2 }), 'login-prompt');
});

test('recommendations are hidden when the session or submitted profile is stale', () => {
  const submitted = profileSnapshot(profile);
  const common = { authenticated: true, promptRequested: false, resultCount: 2, resultProfile: submitted, activeProfile: submitted };
  assert.equal(recommendationView({ ...common, resultToken: 'old-token', activeToken: 'new-token' }), 'empty');
  assert.equal(recommendationView({ ...common, resultToken: 'token', activeToken: 'token', activeProfile: profileSnapshot({ ...profile, education_level: '10th' }) }), 'empty');
  assert.equal(recommendationView({ ...common, resultToken: 'token', activeToken: 'token' }), 'results');
});
