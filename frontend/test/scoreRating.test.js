import test from 'node:test';
import assert from 'node:assert/strict';
import { scoreRatingControl, updateProfileRating } from '../src/scoreRating.js';
import { profileFromSaved } from '../src/studentProfile.js';
import { loadStudentWorkspace } from '../src/studentWorkspace.js';

const groups = ['interests', 'technical', 'employability'];

test('every rating group shows null and missing values as unassessed with a blank slider value', () => {
  for (const group of groups) {
    const expected = { value: '', unassessed: true, label: 'Not assessed', ariaValueText: 'Not assessed', sliderClass: 'rating-slider-unassessed', progress: null };
    assert.deepEqual(scoreRatingControl(null), expected, group);
    assert.deepEqual(scoreRatingControl(undefined), expected, group);
  }
});

test('null, missing, zero, 50 and 100 produce the intended slider rendering states', () => {
  for (const missing of [null, undefined]) {
    const state = scoreRatingControl(missing);
    assert.equal(state.label, 'Not assessed');
    assert.equal(state.sliderClass, 'rating-slider-unassessed');
    assert.equal(state.progress, null);
    assert.equal(state.value, '');
  }
  for (const value of [0, 50, 100]) {
    const state = scoreRatingControl(value);
    assert.equal(state.label, String(value));
    assert.equal(state.sliderClass, 'rating-slider-assessed');
    assert.equal(state.progress, `${value}%`);
    assert.equal(state.value, value);
  }
});

test('unassessed ratings remain null until an actual slider change occurs', () => {
  const original = { interests: { technology: null }, technical: {}, employability: {} };
  for (const group of groups) {
    const control = scoreRatingControl(original[group].example);
    assert.equal(control.unassessed, true);
    assert.equal(control.value, '');
    assert.equal(original[group].example, undefined);
  }
  assert.equal(original.interests.technology, null);
});

test('deliberate slider changes save explicit zero and nonzero ratings in each group', () => {
  for (const group of groups) {
    const blank = { [group]: { example: null } };
    const zero = updateProfileRating(blank, group, 'example', '0');
    const nonzero = updateProfileRating(blank, group, 'example', '63');
    assert.equal(zero[group].example, 0);
    assert.equal(nonzero[group].example, 63);
    assert.equal(scoreRatingControl(zero[group].example).label, '0');
    assert.equal(scoreRatingControl(nonzero[group].example).label, '63');
  }
});

test('emptying a slider value returns it to null without assigning a default', () => {
  const rated = { technical: { programming: 42 } };
  const cleared = updateProfileRating(rated, 'technical', 'programming', '');
  assert.equal(cleared.technical.programming, null);
  assert.deepEqual(scoreRatingControl(cleared.technical.programming), { value: '', unassessed: true, label: 'Not assessed', ariaValueText: 'Not assessed', sliderClass: 'rating-slider-unassessed', progress: null });
});

test('ratings including zero, nonzero and null survive profile save and hydration', () => {
  const profile = {
    interests: { technology: 0, research: 56, design: null },
    technical: { programming: 0, python: 81 },
    employability: { teamwork: null, communication: 74 },
  };
  const hydrated = profileFromSaved(JSON.parse(JSON.stringify(profile)));
  assert.equal(hydrated.interests.technology, 0);
  assert.equal(hydrated.interests.research, 56);
  assert.equal(hydrated.interests.design, null);
  assert.equal(hydrated.technical.programming, 0);
  assert.equal(hydrated.technical.python, 81);
  assert.equal(hydrated.employability.teamwork, null);
  assert.equal(hydrated.employability.communication, 74);
  assert.equal(scoreRatingControl(hydrated.employability.teamwork).label, 'Not assessed');
});

test('authenticated workspace hydration preserves saved values for all three slider groups', async () => {
  const responseProfile = {
    interests: { technology: 0, research: 56, creativity: null },
    technical: { programming: 0, python: 81 },
    employability: { teamwork: null, communication: 74 },
  };
  const workspace = await loadStudentWorkspace('/api', { student_id: 'STU000009', token: 'student-token' }, async url => {
    if (url.includes('/student/profile')) return { ok: true, json: async () => ({ profile: responseProfile }) };
    return { ok: true, json: async () => ({ attempts: [] }) };
  });
  for (const [group, values] of Object.entries(responseProfile)) assert.deepEqual(workspace.profile[group], values);
  assert.equal(scoreRatingControl(workspace.profile.interests.technology).value, 0);
  assert.equal(scoreRatingControl(workspace.profile.technical.python).value, 81);
  assert.equal(scoreRatingControl(workspace.profile.employability.teamwork).label, 'Not assessed');
});
