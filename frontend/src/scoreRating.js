export function scoreRatingControl(score) {
  const unassessed = score === undefined || score === null;
  return {
    value: unassessed ? '' : score,
    unassessed,
    label: unassessed ? 'Not assessed' : String(score),
    ariaValueText: unassessed ? 'Not assessed' : `${score} out of 100`,
    sliderClass: unassessed ? 'rating-slider-unassessed' : 'rating-slider-assessed',
    progress: unassessed ? null : `${score}%`,
  };
}

export function updateProfileRating(profile, section, key, rawValue) {
  const value = rawValue === '' ? null : Number(rawValue);
  return { ...profile, [section]: { ...(profile[section] || {}), [key]: value } };
}
