import test from 'node:test';
import assert from 'node:assert/strict';
import { aptitudeStartState } from '../src/aptitudeAssessment.js';

test('starts an aptitude attempt only when the response contains questions', () => {
  const state = aptitudeStartState(201, {
    attempt_id: 42,
    questions: [{ question_id: 'APT001' }],
    assessment_notice: 'Project-level exercise',
  });
  assert.equal(state.phase, 'taking');
  assert.equal(state.attemptId, 42);
  assert.equal(state.questions.length, 1);
});

test('shows an unavailable state for the explicit empty-question response', () => {
  const state = aptitudeStartState(409, {
    code: 'APTITUDE_QUESTION_BANK_EMPTY',
    error: 'No active aptitude questions are configured for this education level. No attempt was created.',
  });
  assert.equal(state.phase, 'unavailable');
  assert.equal(state.attemptId, null);
  assert.match(state.message, /No active aptitude questions/);
});

test('fails closed if an older or unexpected API response has no question list', () => {
  const state = aptitudeStartState(201, { attempt_id: 99, questions: [] });
  assert.equal(state.phase, 'unavailable');
  assert.equal(state.attemptId, null);
  assert.equal(state.questions.length, 0);
});
