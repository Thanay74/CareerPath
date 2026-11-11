export function subjectRatingControl(subjects, name) {
  const score = subjects?.[name];
  const unassessed = score === undefined || score === null;
  return {
    type: 'number',
    value: unassessed ? '' : score,
    label: unassessed ? 'Not assessed' : String(score),
  };
}

export function updateSubjectRating(profile, name, rawValue) {
  const value = rawValue === '' ? null : Number(rawValue);
  return { ...profile, subjects: { ...(profile.subjects || {}), [name]: value } };
}

export function addUnassessedSubject(profile, name) {
  return { ...profile, subjects: { ...(profile.subjects || {}), [name]: null } };
}
