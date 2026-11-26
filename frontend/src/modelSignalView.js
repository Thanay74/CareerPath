export function modelSignalView(career = {}) {
  const probability = career.ml_family_probability;
  const provisional = career.recommendation_type === 'provisional'
    || career.evidence_coverage?.sufficient === false;
  const available = !provisional && career.ml_status !== 'unavailable'
    && typeof probability === 'number'
    && Number.isFinite(probability);
  return {
    available,
    provisional,
    probability: available ? probability : null,
    legacyMetadata: available && career.model_validation_status === 'legacy_compatible',
    scoreLabel: provisional ? 'provisional suggestion'
      : available ? 'exploratory compatibility estimate' : 'personalized estimate',
    modelFamilyLabel: available ? 'experimental model-family signal' : '',
    unavailableMessage: provisional
      ? 'More assessment information is needed before showing a personalized score.'
      : available ? '' : 'Model-family signal unavailable; compatibility-only guidance.',
  };
}

export function generatedRecommendationDisposition(response = {}) {
  if (response.freshness === 'current') return 'current';
  if (response.model_status === 'unavailable' && Array.isArray(response.recommendations)) return 'compatibility-only';
  return 'unverified';
}
