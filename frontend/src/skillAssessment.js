export function normalizeSkillName(value) {
  return String(value || '').toLocaleLowerCase().match(/[a-z0-9]+/g)?.join(' ') || '';
}

export function customSkillKey(name) {
  return `custom:${normalizeSkillName(name).replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '')}`;
}

export function filterOptionalSkillGroups(catalog, query = '') {
  const normalizedQuery = String(query).trim().toLocaleLowerCase();
  return [
    ['general_digital_skills', 'Other digital skills'],
    ['advanced_self_acquired_skills', 'Advanced and self-acquired skills'],
  ].map(([key, title]) => [key, title, (catalog?.[key] || []).filter(skill =>
    !normalizedQuery || skill.name.toLocaleLowerCase().includes(normalizedQuery),
  )]);
}

export function validateCustomSkill(name, skills, existing = [], editingKey = '') {
  const normalized = normalizeSkillName(name);
  if (!normalized) return 'Enter a skill name.';
  if (normalized.length > 128 || String(name).trim().length > 255) return 'Skill name is too long.';
  if (existing.some(item => item.skill_key !== editingKey && normalizeSkillName(item.display_name) === normalized)) return 'That skill is already in your list.';
  const standard = skills.flatMap(group => group || []).find(item => [item.name, item.key, ...(item.aliases || [])].some(value => normalizeSkillName(value) === normalized));
  if (standard) return `Use the provided ${standard.name} skill instead of adding a duplicate.`;
  return '';
}

export function setSkillApplicability(profile, skill, applicability) {
  const category = skill.category;
  const canonical = skill.canonical_skill || skill.key;
  const details = (profile.skill_assessments || []).filter(item => item.skill_key !== skill.key);
  if (applicability === 'not_applicable') {
    const normalized = normalizeSkillName(skill.name);
    details.push({
      skill_key: skill.key, normalized_name: normalized, display_name: skill.name,
      category, applicability, proficiency: null, source_context: null,
      canonical_skill: skill.canonical_skill || null, is_custom: false,
    });
  }
  const values = { ...(profile[category] || {}) };
  if (applicability === 'not_applicable') delete values[canonical];
  return { ...profile, [category]: values, skill_assessments: details };
}

export function addCustomSkill(profile, { name, category, proficiency, source_context = '' }) {
  const normalized = normalizeSkillName(name);
  return {
    ...profile,
    skill_assessments: [...(profile.skill_assessments || []), {
      skill_key: customSkillKey(name), normalized_name: normalized, display_name: String(name).trim(),
      category, applicability: 'assessed', proficiency: Number(proficiency),
      source_context: source_context || null, canonical_skill: null, is_custom: true,
    }],
  };
}

export function updateCustomSkill(profile, skillKey, changes) {
  return {
    ...profile,
    skill_assessments: (profile.skill_assessments || []).map(item => item.skill_key !== skillKey ? item : {
      ...item, ...changes,
      ...(changes.display_name !== undefined ? {
        display_name: String(changes.display_name).trim(),
        normalized_name: normalizeSkillName(changes.display_name),
      } : {}),
    }),
  };
}

export function removeCustomSkill(profile, skillKey) {
  return { ...profile, skill_assessments: (profile.skill_assessments || []).filter(item => item.skill_key !== skillKey) };
}
