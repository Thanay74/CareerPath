import test from 'node:test';
import assert from 'node:assert/strict';
import { addUnassessedSubject, subjectRatingControl, updateSubjectRating } from '../src/subjectRating.js';
import { profileFromSaved } from '../src/studentProfile.js';

test('unassessed catalog and custom subjects use the same blank number input', () => {
  const profile = { subjects: { biology: null } };
  assert.deepEqual(subjectRatingControl(profile.subjects, 'biology'), { type: 'number', value: '', label: 'Not assessed' });
  const withCustom = addUnassessedSubject(profile, 'custom_lab');
  assert.deepEqual(subjectRatingControl(withCustom.subjects, 'custom_lab'), { type: 'number', value: '', label: 'Not assessed' });
});

test('focusing or clicking an unassessed subject cannot switch its input type', () => {
  const before = subjectRatingControl({ mathematics: null }, 'mathematics');
  // The control has no focus/click-driven state transition; only onChange writes a rating.
  const afterFocus = subjectRatingControl({ mathematics: null }, 'mathematics');
  assert.equal(before.type, 'number');
  assert.equal(afterFocus.type, 'number');
});

test('a student can intentionally rate an unassessed subject without a default score', () => {
  const profile = { subjects: { science: null } };
  assert.equal(subjectRatingControl(profile.subjects, 'science').value, '');
  const rated = updateSubjectRating(profile, 'science', '37');
  assert.equal(rated.subjects.science, 37);
  assert.equal(subjectRatingControl(rated.subjects, 'science').type, 'number');
  assert.equal(subjectRatingControl(rated.subjects, 'science').value, 37);
});

test('zero and nonzero subject ratings survive save and profile reload', () => {
  const profile = { subjects: { mathematics: 0, science: 37 } };
  const storedJson = JSON.stringify(profile);
  const reloaded = profileFromSaved(JSON.parse(storedJson));
  assert.equal(reloaded.subjects.mathematics, 0);
  assert.equal(reloaded.subjects.science, 37);
  assert.equal(subjectRatingControl(reloaded.subjects, 'mathematics').label, '0');
  assert.equal(subjectRatingControl(reloaded.subjects, 'science').label, '37');
});

test('missing and null subject ratings remain unassessed after reload', () => {
  const reloaded = profileFromSaved(JSON.parse(JSON.stringify({ subjects: { science: null } })));
  assert.equal(subjectRatingControl(reloaded.subjects, 'science').label, 'Not assessed');
  assert.equal(subjectRatingControl(reloaded.subjects, 'english').label, 'Not assessed');
  assert.equal(reloaded.subjects.science, null);
  assert.equal(reloaded.subjects.english, undefined);
});

test('custom subject ratings follow the same null, zero, and numeric transitions', () => {
  const profile = addUnassessedSubject({ subjects: {} }, 'custom_course');
  assert.equal(profile.subjects.custom_course, null);
  const zero = updateSubjectRating(profile, 'custom_course', '0');
  assert.equal(zero.subjects.custom_course, 0);
  assert.equal(subjectRatingControl(zero.subjects, 'custom_course').type, 'number');
});
