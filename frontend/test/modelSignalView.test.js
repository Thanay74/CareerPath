import test from 'node:test';
import assert from 'node:assert/strict';
import { generatedRecommendationDisposition, modelSignalView } from '../src/modelSignalView.js';
import { modelExplanationView } from '../src/modelExplanationView.js';

test('sufficient-evidence results label the synthetic model-family signal separately', () => {
  assert.deepEqual(modelSignalView({ ml_status: 'available', ml_family_probability: 72.4 }), {
    available: true, provisional: false, probability: 72.4, legacyMetadata: false,
    scoreLabel: 'exploratory compatibility estimate',
    modelFamilyLabel: 'experimental model-family signal', unavailableMessage: '',
  });
});

test('ML failure never exposes a family score and labels the compatibility-only estimate', () => {
  const view = modelSignalView({ ml_status: 'unavailable', ml_family_probability: 0 });
  assert.equal(view.available, false);
  assert.equal(view.provisional, false);
  assert.equal(view.probability, null);
  assert.equal(view.scoreLabel, 'personalized estimate');
  assert.match(view.unavailableMessage, /compatibility-only/);
});

test('sparse evidence hides legacy model scores even if an older response includes them', () => {
  const view = modelSignalView({ recommendation_type: 'provisional',
    evidence_coverage: { sufficient: false }, ml_status: 'available', ml_family_probability: 91 });
  assert.equal(view.available, false);
  assert.equal(view.provisional, true);
  assert.equal(view.probability, null);
  assert.match(view.unavailableMessage, /More assessment information/);
});

test('legacy model metadata and unavailable SHAP stay distinguishable', () => {
  const view = modelSignalView({ ml_status: 'available', ml_family_probability: 48,
    model_validation_status: 'legacy_compatible' });
  assert.equal(view.legacyMetadata, true);
  assert.equal(modelSignalView({ ml_status: 'available', ml_family_probability: null }).available, false);
});

test('generated results with an unavailable model remain visible as compatibility-only, not current', () => {
  assert.equal(generatedRecommendationDisposition({ freshness: 'current', model_status: 'available', recommendations: [] }), 'current');
  assert.equal(generatedRecommendationDisposition({ freshness: 'unverified', model_status: 'unavailable', recommendations: [{}] }), 'compatibility-only');
  assert.equal(generatedRecommendationDisposition({ freshness: 'stale', recommendations: [] }), 'unverified');
});

test('SHAP probability and raw-margin spaces have distinct language; missing output space is unavailable', () => {
  assert.match(modelExplanationView({ method: 'SHAP TreeExplainer', output_space: 'probability', contributions: [1] }).message, /synthetic-data model-family/);
  assert.match(modelExplanationView({ method: 'SHAP TreeExplainer', output_space: 'raw_margin', contributions: [1] }).message, /not probability points/);
  assert.equal(modelExplanationView({ method: 'SHAP TreeExplainer', contributions: [1] }).available, false);
});
