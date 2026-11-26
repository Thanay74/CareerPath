import test from 'node:test';
import assert from 'node:assert/strict';
import { emptyStudentProfile, profileFromSaved } from '../src/studentProfile.js';
import { addCustomSkill, customSkillKey, filterOptionalSkillGroups, normalizeSkillName, removeCustomSkill, setSkillApplicability, updateCustomSkill, validateCustomSkill } from '../src/skillAssessment.js';

test('skill name normalization is stable and display casing remains intact', () => {
  assert.equal(normalizeSkillName('  Financial Analysis! '), 'financial analysis');
  assert.equal(customSkillKey('Financial Analysis'), 'custom:financial_analysis');
});

test('custom skills preserve proficiency, context, and original display name through hydration', () => {
  const added = addCustomSkill(emptyStudentProfile(), { name: 'TallyPrime', category: 'technical', proficiency: 0, source_context: 'self_learning' });
  const loaded = profileFromSaved(JSON.parse(JSON.stringify(added)));
  assert.equal(loaded.skill_assessments[0].display_name, 'TallyPrime');
  assert.equal(loaded.skill_assessments[0].proficiency, 0);
  assert.equal(loaded.skill_assessments[0].source_context, 'self_learning');
  assert.equal(loaded.skill_assessments[0].applicability, 'assessed');
});

test('blank names, duplicate custom names, and standardized-skill aliases are rejected', () => {
  const skills = [[{ key: 'python', name: 'Python', aliases: ['python programming'] }]];
  assert.match(validateCustomSkill('  ', skills), /Enter a skill name/);
  const existing = [{ skill_key: 'custom:tally', display_name: 'Tally' }];
  assert.match(validateCustomSkill(' tally ', [], existing), /already in your list/);
  assert.match(validateCustomSkill('Python programming', skills), /provided Python/);
});

test('custom skills can be edited and removed without changing unrelated profile data', () => {
  let profile = addCustomSkill(emptyStudentProfile(), { name: 'Tally', category: 'technical', proficiency: 45, source_context: 'course' });
  const key = profile.skill_assessments[0].skill_key;
  profile = updateCustomSkill(profile, key, { display_name: 'Tally Prime', proficiency: 65, source_context: 'certification' });
  assert.equal(profile.skill_assessments[0].display_name, 'Tally Prime');
  assert.equal(profile.skill_assessments[0].proficiency, 65);
  assert.equal(profile.skill_assessments[0].source_context, 'certification');
  profile = removeCustomSkill(profile, profile.skill_assessments[0].skill_key);
  assert.deepEqual(profile.skill_assessments, []);
  assert.deepEqual(profile.subjects, {});
});

test('not applicable is distinct from unknown and an explicit zero rating', () => {
  const profile = { ...emptyStudentProfile(), technical: { python: 0, sql: 80 }, skill_assessments: [] };
  const skill = { key: 'python', name: 'Python', category: 'technical', canonical_skill: 'python' };
  const marked = setSkillApplicability(profile, skill, 'not_applicable');
  assert.equal(marked.technical.python, undefined);
  assert.equal(marked.technical.sql, 80);
  assert.equal(marked.skill_assessments[0].applicability, 'not_applicable');
  const restored = setSkillApplicability(marked, skill, 'assessed');
  assert.deepEqual(restored.skill_assessments, []);
  assert.equal(restored.technical.python, undefined);
});

test('optional digital and advanced skills are searchable without assigning ratings', () => {
  const catalog = {
    domain_skills: [{ key: 'accounting', name: 'Accounting' }],
    general_digital_skills: [{ key: 'excel', name: 'Spreadsheets (Excel or equivalent)' }],
    advanced_self_acquired_skills: [{ key: 'python', name: 'Python' }, { key: 'sql', name: 'SQL / relational databases' }],
    employability_skills: [{ key: 'teamwork', name: 'Teamwork' }],
  };
  const optional = filterOptionalSkillGroups(catalog);
  assert.deepEqual(optional.map(([key]) => key), ['general_digital_skills', 'advanced_self_acquired_skills']);
  assert.deepEqual(optional.flatMap(([, , skills]) => skills).map(skill => skill.key), ['excel', 'python', 'sql']);
  assert.deepEqual(filterOptionalSkillGroups(catalog, 'PYTHON').flatMap(([, , skills]) => skills).map(skill => skill.key), ['python']);
  const untouched = emptyStudentProfile();
  assert.deepEqual(untouched.technical, {});
  assert.deepEqual(untouched.skill_assessments, []);
});

test('standardized display labels retain the catalogue key in the not-applicable payload', () => {
  const skill = { key: 'tally', name: 'Tally / accounting software', category: 'technical', canonical_skill: 'tally' };
  const marked = setSkillApplicability(emptyStudentProfile(), skill, 'not_applicable');
  assert.deepEqual(marked.skill_assessments, [{
    skill_key: 'tally', normalized_name: 'tally accounting software', display_name: 'Tally / accounting software',
    category: 'technical', applicability: 'not_applicable', proficiency: null, source_context: null,
    canonical_skill: 'tally', is_custom: false,
  }]);
  assert.deepEqual(marked.technical, {});
});
