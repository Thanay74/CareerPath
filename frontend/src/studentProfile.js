export const emptyAcademicHistory = level => {
  const common = { study_status: 'unknown', subjects_status: 'unknown', subjects: [] };
  if (level === '12th') return { ...common, mathematics: 'unknown' };
  if (level === "Master's") return { ...common, previous_degree_status: 'unknown', previous_degree: '' };
  return common;
};

export const academicHistoryForProgramChange = profile => {
  const next = emptyAcademicHistory(profile.education_level);
  if (profile.education_level === "Master's") {
    const previous = profile.academic_history || {};
    next.previous_degree_status = previous.previous_degree_status || 'unknown';
    next.previous_degree = previous.previous_degree || '';
  }
  return next;
};

export const updateAcademicHistory = (profile, key, value) => {
  const history = { ...emptyAcademicHistory(profile.education_level), ...profile.academic_history };
  if (key === 'subjects_status' && value !== 'selected') return { ...history, subjects_status: value, subjects: [] };
  if (key === 'mathematics' && value === 'no') {
    return { ...history, mathematics: value, subjects: history.subjects.filter(subject => !/^math(?:s|ematics)?$/i.test(subject.trim())) };
  }
  return { ...history, [key]: value };
};

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
  academic_history: emptyAcademicHistory('12th'),
  subjects: {},
  aptitude: {},
  interests: {},
  technical: {},
  employability: {},
  skill_assessments: [],
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
    academic_history: saved.academic_history && typeof saved.academic_history === 'object' && !Array.isArray(saved.academic_history)
      ? { ...emptyAcademicHistory(saved.education_level || base.education_level), ...saved.academic_history }
      : emptyAcademicHistory(saved.education_level || base.education_level),
    subjects: scoreMap(saved.subjects),
    aptitude: scoreMap(saved.aptitude),
    interests: scoreMap(saved.interests),
    technical: scoreMap(saved.technical),
    employability: scoreMap(saved.employability),
    skill_assessments: Array.isArray(saved.skill_assessments)
      ? saved.skill_assessments.filter(item => item && typeof item === 'object' && !Array.isArray(item)).map(item => ({ ...item }))
      : [],
  };
}

export const emptyAptitudeState = () => ({ phase: 'idle', attemptId: null, questions: [], index: 0, answers: {}, result: null });
