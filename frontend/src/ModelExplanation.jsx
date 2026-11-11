import React from 'react';

function ExplanationDetails({ explanation, scope }) {
  const available = explanation?.method === 'SHAP TreeExplainer' && explanation.contributions?.length;
  return <details className="model-explain">
    <summary>Model-family signal · explainability</summary>
    {available ? <>
      <p>SHAP describes the {explanation.target_family?.replaceAll('_', ' ')} family score ({Math.round((explanation.target_family_probability || 0) * 100)}%). The model's top predicted family was {explanation.predicted_family?.replaceAll('_', ' ') || 'not available'}. {scope}</p>
      <div className="admin-tags">{explanation.contributions.map(item => <span key={item.feature}>{item.feature.replaceAll('_', ' ')} · {item.direction}</span>)}</div>
    </> : <p>SHAP is unavailable for this result. The model-family signal is shown separately; pathway compatibility is explained by the assessed evidence and guidance rules above. {scope}</p>}
  </details>;
}

export default function ModelExplanation({ explanation, explanations, scope }) {
  if (Array.isArray(explanations) && explanations.length) return <section className="model-signal-group" aria-label="Model family explanations">
    <p className="field-note">These model explanations describe grouped family predictions only. They do not independently explain a specific school pathway or establish admission or success.</p>
    {explanations.map(item => <ExplanationDetails key={item.target_family || item.model || JSON.stringify(item)} explanation={item} scope={scope} />)}
  </section>;
  if (!explanation) return null;
  return <ExplanationDetails explanation={explanation} scope={scope} />;
}
