import test from 'node:test';
import assert from 'node:assert/strict';
import { academicHistoryForProgramChange, emptyAptitudeState, emptyStudentProfile, profileFromSaved, updateAcademicHistory } from '../src/studentProfile.js';
import { loadStudentWorkspace } from '../src/studentWorkspace.js';

test('a new account with no saved assessments has unassessed score maps', () => {
  const profile = profileFromSaved({ education_level: '10th', stream: '' });
  for (const group of ['subjects', 'interests', 'technical', 'employability', 'aptitude']) {
    assert.deepEqual(profile[group], {});
  }
  assert.deepEqual(emptyStudentProfile().subjects, {});
  assert.deepEqual(emptyAptitudeState().result, null);
});

test('logout then another student login replaces prior scores rather than merging', () => {
  const studentA = profileFromSaved({
    education_level: "Bachelor's", subjects: { programming: 87 }, interests: { technology: 78 },
    technical: { python: 91 }, employability: { teamwork: 82 }, aptitude: { logical_reasoning: 90 },
  });
  const afterLogout = emptyStudentProfile();
  const studentB = profileFromSaved({ education_level: '10th', subjects: {}, interests: {}, technical: {}, employability: {}, aptitude: {} });
  assert.deepEqual(afterLogout.technical, {});
  assert.deepEqual(studentB.subjects, {});
  assert.deepEqual(studentB.interests, {});
  assert.deepEqual(studentB.technical, {});
  assert.deepEqual(studentB.employability, {});
  assert.deepEqual(studentB.aptitude, {});
  assert.equal(studentB.technical.python, undefined);
  assert.equal(studentA.technical.python, 91);
});

test('student A sees their own saved ratings again after a later login', () => {
  const savedA = { education_level: "Bachelor's", subjects: { programming: 87 }, interests: { technology: 78 }, technical: { python: 91, javascript: 100 }, employability: { teamwork: 82 }, aptitude: { logical_reasoning: 90 } };
  const firstLogin = profileFromSaved(savedA);
  const secondLoginAfterB = profileFromSaved(savedA);
  assert.deepEqual(secondLoginAfterB, firstLogin);
  assert.equal(secondLoginAfterB.subjects.programming, 87);
  assert.equal(secondLoginAfterB.interests.technology, 78);
  assert.equal(secondLoginAfterB.technical.python, 91);
  assert.equal(secondLoginAfterB.technical.javascript, 100);
});

test('missing fields stay absent and real zero remains a scored value', () => {
  const profile = profileFromSaved({ education_level: '12th', subjects: { mathematics: 0, physics: null } });
  assert.equal(profile.subjects.mathematics, 0);
  assert.equal(profile.subjects.physics, null);
  assert.equal(profile.subjects.chemistry, undefined);
  assert.equal(profile.interests.technology, undefined);
  assert.equal(profile.technical.python, undefined);
  assert.equal(profile.employability.teamwork, undefined);
});

test('academic history hydrates as unknown without inventing subjects or credentials', () => {
  const profile = profileFromSaved({ education_level: '12th' });
  assert.deepEqual(profile.academic_history, {
    study_status: 'unknown', subjects_status: 'unknown', subjects: [], mathematics: 'unknown',
  });
});

test('academic history round trips distinct Commerce math and degree history values', () => {
  const saved = profileFromSaved({ education_level: '12th', academic_history: {
    study_status: 'completed', subjects_status: 'selected', subjects: ['Accountancy', 'Economics'], mathematics: 'no',
  } });
  const reloaded = profileFromSaved(JSON.parse(JSON.stringify(saved)));
  assert.deepEqual(reloaded.academic_history, saved.academic_history);
  assert.equal(reloaded.academic_history.mathematics, 'no');
  const master = profileFromSaved({ education_level: "Master's", academic_history: {
    study_status: 'current', subjects_status: 'unknown', subjects: [], previous_degree_status: 'provided', previous_degree: 'BCA',
  } });
  assert.equal(profileFromSaved(JSON.parse(JSON.stringify(master))).academic_history.previous_degree, 'BCA');
});

test('changing a Masters program clears its subject facts but preserves the prior Bachelor degree', () => {
  const profile = profileFromSaved({ education_level: "Master's", academic_history: {
    study_status: 'current', subjects_status: 'selected', subjects: ['Machine Learning'],
    previous_degree_status: 'provided', previous_degree: 'BCA',
  } });
  assert.deepEqual(academicHistoryForProgramChange(profile), {
    study_status: 'unknown', subjects_status: 'unknown', subjects: [],
    previous_degree_status: 'provided', previous_degree: 'BCA',
  });
});

test('changing academic-history answers clears contradictory subject selections', () => {
  const history = { education_level: '12th', academic_history: {
    subjects_status: 'selected', subjects: ['Mathematics', 'Accountancy'], mathematics: 'yes',
  } };
  assert.deepEqual(updateAcademicHistory(history, 'mathematics', 'no').subjects, ['Accountancy']);
  assert.deepEqual(updateAcademicHistory(history, 'subjects_status', 'not_applicable').subjects, []);
});

test('workspace hydration uses only the authenticated student ID and bearer token', async () => {
  const calls = [];
  const workspace = await loadStudentWorkspace('/api', { student_id: 'STU000002', token: 'token-b' }, async (url, options) => {
    calls.push([url, options.headers.Authorization]);
    if (url.includes('/student/profile')) return { ok: true, json: async () => ({ profile: { education_level: '10th', technical: { python: 20 } } }) };
    if (url.includes('/recommendations')) return { ok: true, json: async () => ({ freshness: 'none', recommendations: [] }) };
    return { ok: true, json: async () => ({ attempts: [] }) };
  });
  assert.deepEqual(calls, [
    ['/api/student/profile?student_id=STU000002', 'Bearer token-b'],
    ['/api/recommendations?student_id=STU000002', 'Bearer token-b'],
    ['/api/aptitude/history?student_id=STU000002', 'Bearer token-b'],
  ]);
  assert.deepEqual(workspace.profile.technical, { python: 20 });
  assert.equal(workspace.aptitude.phase, 'idle');
  assert.deepEqual(workspace.recommendationState, { freshness: 'none', recommendations: [], snapshot: undefined, message: '' });
});
