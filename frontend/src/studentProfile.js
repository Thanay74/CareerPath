export const emptyStudentProfile = () => ({
  education_level: '12th',
  stream: '',
  degree: '',
  specialization: '',
  study_period: '',
  academic_performance: null,
  academic_scale: 'percentage',
  research_interests: '',
  career_preferences: '',
  subjects: {},
  aptitude: {},
  interests: {},
  technical: {},
  employability: {},
});

const scoreMap = value => value && typeof value === 'object' && !Array.isArray(value) ? { ...value } : {};

// Replace profile state from the authenticated account. Never merge this with
// another account's prior in-memory scores.
export function profileFromSaved(saved) {
  const base = emptyStudentProfile();
  if (!saved || typeof saved !== 'object' || Array.isArray(saved)) return base;
  return {
    ...base,
    ...saved,
    subjects: scoreMap(saved.subjects),
    aptitude: scoreMap(saved.aptitude),
    interests: scoreMap(saved.interests),
    technical: scoreMap(saved.technical),
    employability: scoreMap(saved.employability),
  };
}

export const emptyAptitudeState = () => ({ phase: 'idle', attemptId: null, questions: [], index: 0, answers: {}, result: null });
