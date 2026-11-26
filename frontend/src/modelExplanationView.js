export function modelExplanationView(explanation = {}) {
  const available = explanation.method === 'SHAP TreeExplainer'
    && Array.isArray(explanation.contributions)
    && explanation.contributions.length > 0
    && ['probability', 'raw_margin'].includes(explanation.output_space);
  if (!available) return { available: false, message: 'SHAP explanation unavailable or its output space could not be verified.' };
  return {
    available: true,
    message: explanation.output_space === 'raw_margin'
      ? 'SHAP contributions describe a raw model margin; they are not probability points.'
      : 'SHAP contributions describe a synthetic-data model-family classification output; they do not describe career success or admission probability.',
  };
}
