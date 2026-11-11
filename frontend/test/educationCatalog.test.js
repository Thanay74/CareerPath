import test from 'node:test';
import assert from 'node:assert/strict';
import { educationOptions, fetchEducationCatalog, subjectsForProfile } from '../src/educationCatalog.js';

const response = (body, status = 200) => ({ ok: status >= 200 && status < 300, status, json: async () => body });

test('loads a successful catalog response and returns level-specific pathways and subjects', async () => {
  const catalog = { levels: {
    '10th': { streams: ['Science', 'Commerce'], degrees: [], subjects: { default: ['math', 'english'] } },
    '12th': { streams: ['Science PCB', 'Commerce'], degrees: [], subjects: { Commerce: ['accountancy'] } },
    "Bachelor's": { streams: [], degrees: ['BCA', 'B.Com'], subjects: { BCA: ['programming'] } },
    "Master's": { streams: [], degrees: ['MCA'], subjects: { MCA: ['advanced_programming'] } },
  } };
  const result = await fetchEducationCatalog('/api', async url => {
    assert.equal(url, '/api/education/catalog');
    return response(catalog);
  });
  assert.deepEqual(educationOptions(result, '10th'), ['Science', 'Commerce']);
  assert.deepEqual(educationOptions(result, '12th'), ['Science PCB', 'Commerce']);
  assert.deepEqual(educationOptions(result, "Bachelor's"), ['BCA', 'B.Com']);
  assert.deepEqual(educationOptions(result, "Master's"), ['MCA']);
  assert.deepEqual(subjectsForProfile(result, { education_level: '10th' }), ['math', 'english']);
  assert.deepEqual(subjectsForProfile(result, { education_level: '12th', stream: 'Commerce' }), ['accountancy']);
  assert.deepEqual(subjectsForProfile(result, { education_level: "Bachelor's", degree: 'BCA' }), ['programming']);
  assert.deepEqual(subjectsForProfile(result, { education_level: "Master's", degree: 'MCA' }), ['advanced_programming']);
});

test('keeps a valid empty catalog distinct from an API failure', async () => {
  const catalog = await fetchEducationCatalog('/api', async () => response({ levels: {} }));
  assert.deepEqual(catalog, {});
  assert.deepEqual(educationOptions(catalog, '10th'), []);
  await assert.rejects(fetchEducationCatalog('/api', async () => response({ error: 'Unavailable' }, 503)), /Unavailable/);
});

test('reports network errors and malformed catalog responses for retry UI', async () => {
  await assert.rejects(fetchEducationCatalog('/api', async () => { throw new TypeError('offline'); }), /Could not reach the education catalog API/);
  await assert.rejects(fetchEducationCatalog('/api', async () => response({ unexpected: [] })), /missing its levels catalog/);
});

test('returns no stale subjects when the selected level or course has no catalog entry', () => {
  const catalog = { levels: { "Bachelor's": { streams: [], degrees: ['B.Com'], subjects: { 'B.Com': ['accounting'] } } } };
  assert.deepEqual(subjectsForProfile(catalog, { education_level: '10th' }), []);
  assert.deepEqual(subjectsForProfile(catalog, { education_level: "Bachelor's", degree: 'BCA' }), []);
});
