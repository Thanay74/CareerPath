export function aptitudeStartState(status, payload) {
  if (status < 200 || status >= 300) {
    return {
      phase: status === 409 && payload?.code === 'APTITUDE_QUESTION_BANK_EMPTY' ? 'unavailable' : 'error',
      attemptId: null,
      questions: [],
      index: 0,
      answers: {},
      result: null,
      message: payload?.error || 'The aptitude assessment could not be started.',
    };
  }

  const questions = Array.isArray(payload?.questions) ? payload.questions : [];
  if (questions.length === 0) {
    return {
      phase: 'unavailable',
      attemptId: null,
      questions: [],
      index: 0,
      answers: {},
      result: null,
      message: 'No active aptitude questions were returned for this education level. The aptitude assessment cannot be completed yet.',
    };
  }

  return {
    phase: 'taking',
    attemptId: payload.attempt_id,
    questions,
    index: 0,
    answers: {},
    result: null,
    message: payload.assessment_notice || '',
  };
}
