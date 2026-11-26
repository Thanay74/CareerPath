import React from 'react';
import { modelExplanationView } from './modelExplanationView.js';

function ExplanationDetails({ explanation, scope }) {
  const explanationView = modelExplanationView(explanation);
  const available = explanationView.available;
  return <details className="model-explain">
    <summary>Experimental model signal · trained on synthetic data</summary>
    {available ? <>
      <p>{explanationView.message} Family: {explanation.target_family?.replaceAll('_', ' ')}. This is a model-family classification signal, not a probability of career success or admission. The model's top predicted family was {explanation.predicted_family?.replaceAll('_', ' ') || 'not available'}. {scope}</p>
      <div className="admin-tags">{explanation.contributions.map(item => <span key={item.feature}>{item.feature.replaceAll('_', ' ')} · {item.direction}</span>)}</div>
    </> : <p>{explanationView.message} This experimental model-family signal is based on synthetic data and is not a probability of career success or admission. Pathway compatibility is explained by the assessed evidence and guidance rules above. {scope}</p>}
  </details>;
}

export default function ModelExplanation({ explanation, explanations, scope }) {
  if (Array.isArray(explanations) && explanations.length) return <section className="model-signal-group" aria-label="Model family explanations">
    <p className="field-note">These experimental model explanations use synthetic-data-trained family classifiers. They do not independently explain a specific school pathway or predict admission or success.</p>
    {explanations.map(item => <ExplanationDetails key={item.target_family || item.model || JSON.stringify(item)} explanation={item} scope={scope} />)}
  </section>;
  if (!explanation) return null;
  return <ExplanationDetails explanation={explanation} scope={scope} />;
}
